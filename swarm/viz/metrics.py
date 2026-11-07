"""Shared metrics layer for all viz outputs (videos, paper figures, dashboard). Reads run logs only, draws nothing.

Per branch (one game dir):
    load_branch(dir)        -> Branch: per-round edges, scores, wins, God powers, gives, defects
    round_series(b, ever)   -> per-round cumulative counters (welfare, winners, gives, defects, posts, DMs,
                               God moves used, diverged agents), the numbers the video panels show
    game_metrics(dir)       -> end-of-game outcome metrics (definitions match swarm.analysis.grid_results)
    branch_health(dir)      -> LLM calls, cache hits, errors, retries, parse failures, truncation, cost, tokens,
                               latency, price-tier mix
Per pair (branch vs the no-God branch of the same world):
    divergence(a, b)        -> (now, ever) sets of agents whose actions differ per round (ripple metric)
    pair_metrics(...)       -> div_post_fork, div_final_cum (as grid_results), fork round, spread
Per cell (one run dir):
    worlds(run)             -> finished + healthy branches per world (seeds with an unhealthy branch dropped)
    load_cell(run)          -> everything above for every finished world, plus status counts and config
    deltas(cell, m, a, b)   -> per-world a - b;  summarize(xs) -> mean, Student-t 95% CI, bootstrap 95% CI,
                               sign-flip p, sd, n, MDE (80% power, two-sided 5%)
"""

from __future__ import annotations

import json
import random
import statistics
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from swarm.analysis.grid_stats import T975, boot_ci, game_health, signflip_p, t_ci

KINDS = ("dm", "give", "defect", "board", "fraud", "cot")
# outcome metrics shown in tables: key -> (label, short description)
GAME_METRICS: dict[str, tuple[str, str]] = {
    "welfare": ("welfare", "mean final score (share of the 3 needs unlocked)"),
    "win_rate": ("win rate", "share of agents that won"),
    "lost": ("needs lost", "needs lost to the wrong-defect penalty, per agent"),
    "burned": ("needs burned", "needs burned by others' correct defects, per agent"),
    "gives": ("gives", "successful give_key actions per agent"),
    "defects_ok": ("defects", "successful defect actions per agent"),
    "board_posts": ("board posts", "successful board posts per agent"),
    "dms": ("DMs", "successful DMs per agent"),
    "rounds": ("rounds", "rounds played"),
}
PAIR_METRICS: dict[str, tuple[str, str]] = {
    "div_post_fork": ("divergence (post-fork)", "mean share of agents whose round actions differ from no-God, "
                                                "from God's first move on"),
    "div_final_cum": ("divergence (ever)", "share of agents that ever acted differently from no-God"),
}
ACTION_KINDS = {"gives": "give_key", "defects_ok": "defect", "board_posts": "post_board", "dms": "send_message"}
# cheapest list price of openai/gpt-oss-120b on OpenRouter during the grid (plan/GRID_PLAN.md), USD per token
CHEAPEST_PRICE = {"openai/gpt-oss-120b": (0.011e-6, 0.041e-6)}


# ------------------------------------------------------------------ branch
@dataclass
class Power:
    round: int
    power: str              # message_fraud | cot_control
    target: str             # the agent God acts on (DM receiver / notes owner)
    spoofed: str | None     # message_fraud: the real agent the forged DM claims to come from
    text: str


@dataclass
class Branch:
    label: str
    agents: list[str]
    R: int
    rounds_played: int
    end_reason: str
    edges: dict[int, dict[str, list[tuple[str, str]]]]       # round -> kind -> [(src, dst)]
    scores: dict[int, dict[str, float]]                       # round -> agent -> score (round 0 = all 0)
    wins: dict[int, list[str]]
    powers: list[Power] = field(default_factory=list)
    gives: list[tuple[int, str, str, int]] = field(default_factory=list)       # (round, from, to, info_id)
    defects: list[tuple[int, str, str, bool]] = field(default_factory=list)    # (round, actor, target, correct)
    budget: int | None = None                                                 # God's K (cost + budget_left)

    def welfare(self, r: int) -> float:
        s = self.score_at(r)
        return sum(s.values()) / max(1, len(self.agents))

    def score_at(self, r: int) -> dict[str, float]:
        ks = [k for k in self.scores if k <= r]
        return self.scores[max(ks)] if ks else {a: 0.0 for a in self.agents}

    def won_by(self, r: int) -> set[str]:
        return {a for rr, ws in self.wins.items() if rr <= r for a in ws}


def is_done(game_dir: str | Path) -> bool:
    try:
        return json.loads((Path(game_dir) / "meta.json").read_text()).get("status") == "done"
    except (OSError, ValueError):
        return False


def load_branch(game_dir: str | Path) -> Branch:
    game_dir = Path(game_dir)
    ev = [json.loads(ln) for ln in open(game_dir / "events.jsonl", encoding="utf-8")]
    start = next(e for e in ev if e["type"] == "game_start")["data"]
    agents, R = list(start["order"]), int(start["max_rounds"])
    edges: dict[int, dict[str, list[tuple[str, str]]]] = {r: {k: [] for k in KINDS} for r in range(R + 1)}
    scores: dict[int, dict[str, float]] = {0: {a: 0.0 for a in agents}}
    wins: dict[int, list[str]] = {}
    b = Branch(game_dir.name, agents, R, R, "", edges, scores, wins)
    for e in ev:
        r, t, d = e["round"], e["type"], e["data"]
        if r not in edges:
            continue
        if t == "message":
            m = d["message"]
            if m["channel"] == "dm" and m["receiver"] and not m["forged"]:
                edges[r]["dm"].append((m["sender_shown"], m["receiver"]))
        elif t == "action_result" and d["action"]["kind"] == "post_board" and d.get("ok"):
            edges[r]["board"].append((e["actor"], "BOARD"))
        elif t == "key_transfer" and d["cause"] == "give" and d["from_agent"]:
            edges[r]["give"].append((d["from_agent"], d["to_agent"]))
            b.gives.append((r, d["from_agent"], d["to_agent"], int(d["info_id"])))
        elif t == "burn":
            edges[r]["defect"].append((d["actor"], d["target"]))
            b.defects.append((r, d["actor"], d["target"], bool(d["correct"])))
        elif t == "god_power":
            if b.budget is None and d.get("budget_left") is not None:
                b.budget = int(d["budget_left"]) + int(d.get("cost") or 0)
            if not d["ok"]:
                continue
            a = d["action"]
            if d["power"] == "message_fraud":
                edges[r]["fraud"].append(("GOD", a["receiver"]))
                b.powers.append(Power(r, "message_fraud", a["receiver"], a.get("sender"), a.get("text", "")))
            else:
                edges[r]["cot"].append(("GOD", a["agent"]))
                b.powers.append(Power(r, "cot_control", a["agent"], None, a.get("text", "")))
        elif t == "win":
            wins.setdefault(r, []).append(d["agent"])
        elif t == "round_end":
            scores[r] = dict(d["scores"])
        elif t == "game_end":
            o = d["outcome"]
            b.rounds_played, b.end_reason = int(o["rounds_played"]), str(o.get("end_reason", ""))
    return b


ROUND_FIELDS = ("welfare", "winners", "gives", "defects", "defects_correct", "board_posts", "dms", "god_moves",
                "diverged")


def round_series(b: Branch, ever: dict[int, set[str]] | None = None) -> list[dict[str, float]]:
    """Index r (0..R): cumulative counters up to the end of round r (rounds after the game ended repeat the
    final state). `diverged` = agents that have acted differently from the paired no-God branch (needs ever)."""
    out = []
    acc = Counter()
    for r in range(0, b.R + 1):
        if 1 <= r <= b.rounds_played:
            e = b.edges[r]
            acc["gives"] += len(e["give"])
            acc["defects"] += len(e["defect"])
            acc["board_posts"] += len(e["board"])
            acc["dms"] += len(e["dm"])
            acc["defects_correct"] += sum(1 for rr, *_x, ok in b.defects if rr == r and ok)
            acc["god_moves"] += len(e["fraud"]) + len(e["cot"])
        row = {"round": r, "welfare": b.welfare(r), "winners": len(b.won_by(r)), **{k: float(acc[k]) for k in (
            "gives", "defects", "defects_correct", "board_posts", "dms", "god_moves")}}
        row["diverged"] = float(len((ever or {}).get(r, ()))) if ever is not None else float("nan")
        out.append(row)
    return out


def game_metrics(game_dir: str | Path) -> dict[str, float]:
    """End-of-game outcomes, per agent where it says so. Same definitions as swarm.analysis.grid_results."""
    game_dir = Path(game_dir)
    out = json.loads((game_dir / "outcome.json").read_text())
    pa = list(out["per_agent"].values())
    n = max(1, len(pa))
    m = {"welfare": sum(a["score"] for a in pa) / n,
         "win_rate": sum(1 for a in pa if a.get("won_round")) / n,
         "burned": sum(len(a.get("burned") or []) for a in pa) / n,
         "lost": sum(len(a.get("lost") or []) for a in pa) / n,
         "rounds": float(out["rounds_played"])}
    counts = dict.fromkeys(ACTION_KINDS, 0)
    with open(game_dir / "events.jsonl", encoding="utf-8") as f:
        for ln in f:
            if '"type":"action_result"' in ln:
                d = json.loads(ln)["data"]
                if d.get("ok"):
                    for k, kind in ACTION_KINDS.items():
                        counts[k] += d["action"]["kind"] == kind
    m.update({k: c / n for k, c in counts.items()})
    return m


def branch_health(game_dir: str | Path) -> dict[str, Any]:
    """LLM-call health of one branch from llm_calls.jsonl (+ turn parse failures from events.jsonl)."""
    game_dir = Path(game_dir)
    h = Counter()
    lat: list[float] = []
    model = None
    with open(game_dir / "llm_calls.jsonl", encoding="utf-8") as f:
        for ln in f:
            c = json.loads(ln)
            h["calls"] += 1
            rq, rs = c.get("request") or {}, c.get("response") or {}
            model = model or c.get("model")
            if c.get("error"):
                h["errors"] += 1
                continue
            if (rq.get("meta") or {}).get("attempt", 0):
                h["parse_retries"] += 1
            h["http_retries"] += int(rs.get("retries") or 0)
            if rs.get("finish_reason") == "length":       # counted over all responses, as GRID_RESULTS
                h["truncated"] += 1
            if rs.get("cache_hit"):
                h["cache_hits"] += 1
                continue
            h["paid"] += 1
            u = rs.get("usage") or {}
            pt, ct = int(u.get("prompt_tokens") or 0), int(u.get("completion_tokens") or 0)
            h["prompt_tokens"] += pt
            h["completion_tokens"] += ct
            cost = float(rs.get("cost_usd") or 0.0)
            h["cost_usd"] += cost
            if rs.get("latency_s") is not None:
                lat.append(float(rs["latency_s"]))
            ref = CHEAPEST_PRICE.get(rs.get("model") or c.get("model") or "")
            if ref and (pt or ct):
                h["price_cheapest" if cost / (pt * ref[0] + ct * ref[1]) < 1.6 else "price_fallback"] += 1
    with open(game_dir / "events.jsonl", encoding="utf-8") as f:
        for ln in f:
            if '"type":"turn"' in ln:
                td = json.loads(ln)["data"]
                h["turns"] += 1
                h["parse_failures"] += not td.get("parse_ok", True)
    lat.sort()
    out: dict[str, Any] = {k: h[k] for k in ("calls", "paid", "cache_hits", "errors", "parse_retries", "http_retries",
                                              "truncated", "turns", "parse_failures", "prompt_tokens",
                                              "completion_tokens", "price_cheapest", "price_fallback")}
    out["cost_usd"] = h["cost_usd"]
    out["latency_p50"] = lat[len(lat) // 2] if lat else None
    out["latency_p90"] = lat[int(0.9 * (len(lat) - 1))] if lat else None
    out["model"] = model
    out["unhealthy"] = game_health(game_dir)["reasons"]
    return out


# ------------------------------------------------------------------ pair
def divergence(a_dir: str | Path, b_dir: str | Path) -> tuple[dict[int, set[str]], dict[int, set[str]]]:
    """(now, ever): agents whose round-r actions differ between branches / have differed at any round <= r.
    Same coarse action signature as swarm.analysis.ripple (message wording ignored)."""
    from swarm.analysis.ripple import ripple
    from swarm.runlog.trace import load_game

    res = ripple(load_game(a_dir, with_llm_calls=False, with_snapshots=False),
                 load_game(b_dir, with_llm_calls=False, with_snapshots=False))
    now = {r: {a for a in res.agents if res.div[a][i]} for i, r in enumerate(res.rounds)}
    ever = {r: {a for a in res.agents if res.first_div[a] is not None and res.first_div[a] <= r} for r in res.rounds}
    return now, ever


def pair_metrics(branch_dir: Path, nogod_dir: Path, god_dir: Path) -> dict[str, Any]:
    """Divergence of a branch from no-God. div_* as grid_results (fork point and victims from the God branch);
    curve = share of agents diverged so far per round; fork = first round where this branch's actions differ
    (God branch: God's first successful move)."""
    from swarm.analysis.ripple import first_intervention, ripple
    from swarm.runlog.trace import load_game

    tr = {k: load_game(p, with_llm_calls=False, with_snapshots=False)
          for k, p in (("x", branch_dir), ("nogod", nogod_dir), ("god", god_dir))}
    s = ripple(tr["nogod"], tr["x"], fork_from=tr["god"])
    summ = s.summary()
    first_diff = next((r for r, f in zip(s.rounds, s.frac, strict=True) if f > 0), None)
    is_god = Path(branch_dir) == Path(god_dir)
    fi = first_intervention(tr["god"])
    return {"div_post_fork": float(summ["post_fork_mean_frac"] or 0.0), "div_final_cum": float(summ["final_cum"] or 0.0),
            "curve": list(s.cum), "fork": (fi[0] if fi else None) if is_god else first_diff, "first_diff": first_diff}


# ------------------------------------------------------------------ cell
def branch_dirs(run_dir: str | Path) -> dict[int, dict[str, Path]]:
    out: dict[int, dict[str, Path]] = {}
    gd = Path(run_dir) / "games"
    if gd.is_dir():
        for d in sorted(gd.iterdir()):
            idx, _, br = d.name.partition("-")
            if idx[:1] == "g" and idx[1:].isdigit() and br:
                out.setdefault(int(idx[1:]), {})[br] = d
    return out


def worlds(run_dir: str | Path) -> dict[int, dict[str, Path]]:
    """game_idx -> branch -> dir, finished and healthy branches only; seeds with an unhealthy branch dropped
    (as grid_stats); worlds without both god and nogod finished are left out."""
    out: dict[int, dict[str, Path]] = {}
    bad: set[int] = set()
    for i, brs in branch_dirs(run_dir).items():
        for br, d in brs.items():
            if not is_done(d):
                continue
            if game_health(d)["reasons"]:
                bad.add(i)
                continue
            out.setdefault(i, {})[br] = d
    return {i: b for i, b in out.items() if i not in bad and "god" in b and "nogod" in b}


def welfare(game_dir: Path) -> float:
    pa = json.loads((Path(game_dir) / "outcome.json").read_text())["per_agent"].values()
    return sum(a["score"] for a in pa) / max(1, len(pa))


def cell_deltas(run_dir: str | Path, a: str = "god", b: str = "nogod") -> dict[int, float]:
    return {i: welfare(br[a]) - welfare(br[b]) for i, br in worlds(run_dir).items() if a in br and b in br}


def paired_diff(da: dict[int, float], db: dict[int, float]) -> dict[int, float]:
    """db - da over the worlds both cells share (same run.seed => same world per index)."""
    return {i: db[i] - da[i] for i in sorted(set(da) & set(db))}


def cum_curves(run_dir: str | Path, a: str = "god", b: str = "nogod") -> dict[int, list[float]]:
    out = {}
    for i, br in worlds(run_dir).items():
        if a in br and b in br:
            _, ever = divergence(br[a], br[b])
            n = len(load_branch(br[a]).agents)
            out[i] = [len(ever[r]) / n for r in sorted(ever)]
    return out


def aligned_curves(run_dir: str | Path, br: str = "god") -> tuple[dict[int, list[float]], list[int]]:
    """Share of agents diverged from no-God per round, re-indexed to rounds since the branch forked:
    God branch = God's first successful move; other branches = their first round whose actions differ
    (the God-free re-run B' forks at round 1 because it shares no cached replies). -> ({world: curve}, forks)."""
    curves, forks = {}, []
    for i, brs in worlds(run_dir).items():
        if br not in brs:
            continue
        _, ever = divergence(brs[br], brs["nogod"])
        b = load_branch(brs[br])
        n = len(b.agents)
        rs = sorted(ever)
        fork = b.powers[0].round if (br == "god" and b.powers) else next((r for r in rs if ever[r]), None)
        if fork is None:
            continue
        curves[i] = [len(ever[r]) / n for r in rs if r >= fork]
        forks.append(fork)
    return curves, forks


def mean_curve(curves: dict[int, list[float]]) -> list[float]:
    """Pointwise mean; a shorter curve (game ended early) holds its last value."""
    if not curves:
        return []
    L = max(len(ys) for ys in curves.values())
    return [statistics.fmean(ys[min(r, len(ys) - 1)] for ys in curves.values()) for r in range(L)]


def cell_round_means(run_dir: str | Path, fields: tuple[str, ...] = ("welfare", "winners", "gives", "defects"),
                     ) -> dict[str, dict[str, list[float]]]:
    """Mean per-round trajectory over worlds, per branch: {branch: {field: [mean at round 0..R]}}."""
    acc: dict[str, list[list[dict[str, float]]]] = {}
    for brs in worlds(run_dir).values():
        for br, d in brs.items():
            acc.setdefault(br, []).append(round_series(load_branch(d)))
    out: dict[str, dict[str, list[float]]] = {}
    for br, series in acc.items():
        L = min(len(s) for s in series)
        out[br] = {f: [statistics.fmean(s[r][f] for s in series) for r in range(L)] for f in fields}
        out[br]["n"] = [float(len(series))]
    return out


def mde(sd: float, n: int, power_z: float = 0.8416) -> float:
    """Minimum detectable mean paired difference, 80% power, two-sided 5% (t quantile for alpha, z for power)."""
    if n < 2 or sd != sd:
        return float("nan")
    return (T975.get(n - 1, 1.960) + power_z) * sd / n ** 0.5


def summarize(xs: list[float], n_boot: int = 10000, seed: int = 0) -> dict[str, Any]:
    rng = random.Random(seed)
    lo, hi = boot_ci(xs, n_boot, rng)
    tlo, thi = t_ci(xs)
    sd = statistics.stdev(xs) if len(xs) > 1 else float("nan")
    return {"n": len(xs), "mean": statistics.fmean(xs) if xs else float("nan"), "lo": lo, "hi": hi,
            "tlo": tlo, "thi": thi, "p": signflip_p(xs, rng), "sd": sd, "mde": mde(sd, len(xs))}


def run_config(run_dir: str | Path) -> dict[str, Any]:
    """Small config digest from config.resolved.yaml (no YAML parse of unknown keys needed)."""
    import yaml

    p = Path(run_dir) / "config.resolved.yaml"
    if not p.exists():
        return {}
    c = yaml.safe_load(p.read_text()) or {}
    g, r = c.get("game") or {}, c.get("runner") or {}
    fork = r.get("fork") or {}
    god = c.get("god") or {}          # the God branch's God (fork.control_god only shapes the control's ids)
    sched = god.get("schedule") or []
    return {"n_agents": g.get("n_agents"), "max_rounds": g.get("max_rounds"), "turn_mode": g.get("turn_mode"),
            "keys_per_agent": g.get("keys_per_agent"),
            "noise_replica": fork.get("noise_replica"), "god_k": (god.get("budget") or {}).get("k"),
            "god_start": god.get("start_round"),
            "schedule": [f"{s.get('power')}@r{s.get('round')}" for s in sched if isinstance(s, dict)]}


def world_hash(game_dir: str | Path) -> str:
    """Fingerprint of the generated world (agents' starting keys and needs from game_start): two cells play the
    same world for an index only when these match (same run.seed is not enough if N or keys/agent differ)."""
    import hashlib

    with open(Path(game_dir) / "events.jsonl", encoding="utf-8") as f:
        for ln in f:
            if '"type":"game_start"' in ln:
                ag = json.loads(ln)["data"]["agents"]
                core = {a: (sorted(k["copy_id"] for k in v["keys"]), sorted(v["needs"])) for a, v in ag.items()}
                return hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()[:16]
    return ""


def paired_or_unpaired(ca: dict[str, Any], cb: dict[str, Any], metric: str) -> tuple[str, dict[str, Any]]:
    """Contrast of cell b's God effect against cell a's: paired by world when the worlds are identical
    (world_hash), else the difference of the two means with a Welch t 95% CI. Returns (kind, stats)."""
    da, db = deltas(ca, metric, "god"), deltas(cb, metric, "god")
    shared = [i for i in sorted(set(da) & set(db))
              if ca["worlds"][i].get("world_hash") and ca["worlds"][i]["world_hash"] == cb["worlds"][i].get("world_hash")]
    if len(shared) >= 2:
        return "paired", summarize([db[i] - da[i] for i in shared])
    xa, xb = list(da.values()), list(db.values())
    if len(xa) < 2 or len(xb) < 2:
        return "n/a", {}
    va, vb = statistics.variance(xa) / len(xa), statistics.variance(xb) / len(xb)
    se = (va + vb) ** 0.5
    dfw = (va + vb) ** 2 / ((va ** 2 / (len(xa) - 1)) + (vb ** 2 / (len(xb) - 1))) if se else 1
    q = T975.get(max(1, int(dfw)), 1.960)
    m = statistics.fmean(xb) - statistics.fmean(xa)
    return "unpaired", {"n": f"{len(xa)}+{len(xb)}", "mean": m, "tlo": m - q * se, "thi": m + q * se,
                        "p": float("nan"), "lo": float("nan"), "hi": float("nan"), "sd": float("nan"),
                        "mde": float("nan")}


def load_cell(run_dir: str | Path, with_health: bool = True, with_pairs: bool = True) -> dict[str, Any]:
    """Everything the dashboard needs for one cell. Branches still running are counted but not loaded."""
    run_dir = Path(run_dir)
    all_b = branch_dirs(run_dir)
    status = Counter()
    for brs in all_b.values():
        for d in brs.values():
            try:
                status[json.loads((d / "meta.json").read_text()).get("status", "?")] += 1
            except (OSError, ValueError):
                status["no meta"] += 1
    ws = worlds(run_dir)
    unhealthy = sorted({i for i, brs in all_b.items() for d in brs.values()
                        if is_done(d) and game_health(d)["reasons"]})
    cell: dict[str, Any] = {"name": run_dir.name, "path": str(run_dir), "config": run_config(run_dir),
                            "status": dict(status), "n_worlds_total": len(all_b), "unhealthy_worlds": unhealthy,
                            "worlds": {}, "health": {}}
    for i, brs in sorted(ws.items()):
        w: dict[str, Any] = {"branches": {}, "pairs": {}, "world_hash": world_hash(brs["nogod"])}
        for br, d in brs.items():
            w["branches"][br] = game_metrics(d)
            if with_health:
                cell["health"].setdefault(br, []).append(branch_health(d))
        if with_pairs:
            for br, d in brs.items():
                if br != "nogod":
                    w["pairs"][br] = pair_metrics(d, brs["nogod"], brs["god"])
        cell["worlds"][i] = w
    return cell


def deltas(cell: dict[str, Any], metric: str, a: str = "god", b: str = "nogod") -> dict[int, float]:
    """Per-world a - b. Pair metrics (divergence) are a's divergence from no-God (b must be nogod)."""
    out = {}
    for i, w in cell["worlds"].items():
        if metric in PAIR_METRICS:
            if a in w["pairs"] and b == "nogod":
                out[i] = w["pairs"][a][metric]
        elif a in w["branches"] and b in w["branches"]:
            out[i] = w["branches"][a][metric] - w["branches"][b][metric]
    return out


def branch_values(cell: dict[str, Any], metric: str, br: str) -> dict[int, float]:
    return {i: w["branches"][br][metric] for i, w in cell["worlds"].items() if br in w["branches"]}


def edge_counts(edges: list[tuple[str, str]]) -> Counter[tuple[str, str]]:
    return Counter(edges)
