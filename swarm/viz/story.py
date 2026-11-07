"""Data helpers for the demo video and paper figures (no drawing here, so they are unit-testable).

    load_branch(game_dir)            -> Branch: per-round edges, scores, welfare, God powers, gives
    divergence(god_dir, nogod_dir)   -> per-round sets of agents whose actions differ (ripple metric)
    captions(god, nogod, div)        -> {round: [(kind, text), ...]} running caption lines
    pacing(R, captions)              -> [(round, seconds)]: 1 s per round, longer on God events
    world_table(run_dir)             -> per-world deltas (god - nogod, noise - nogod) and ripple speed
    pick_worlds(rows)                -> the data-driven demo picks ("harm" and "ripple")
Only finished branches (meta.json status "done") are used.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

KINDS = ("dm", "give", "defect", "board", "fraud", "cot")


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

    def welfare(self, r: int) -> float:
        s = self.score_at(r)
        return sum(s.values()) / max(1, len(self.agents))

    def score_at(self, r: int) -> dict[str, float]:
        ks = [k for k in self.scores if k <= r]
        return self.scores[max(ks)] if ks else {a: 0.0 for a in self.agents}

    def won_by(self, r: int) -> set[str]:
        return {a for rr, ws in self.wins.items() if rr <= r for a in ws}


def is_done(game_dir: Path) -> bool:
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
        elif t == "god_power" and d["ok"]:
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


def divergence(god_dir: str | Path, nogod_dir: str | Path) -> tuple[dict[int, set[str]], dict[int, set[str]]]:
    """(now, ever): agents whose round-r actions differ between branches / have differed at any round <= r.
    Same coarse action signature as swarm.analysis.ripple (message wording ignored)."""
    from swarm.analysis.ripple import ripple
    from swarm.runlog.trace import load_game

    res = ripple(load_game(god_dir, with_llm_calls=False, with_snapshots=False),
                 load_game(nogod_dir, with_llm_calls=False, with_snapshots=False))
    now = {r: {a for a in res.agents if res.div[a][i]} for i, r in enumerate(res.rounds)}
    ever = {r: {a for a in res.agents if res.first_div[a] is not None and res.first_div[a] <= r} for r in res.rounds}
    return now, ever


def _short(text: str, n: int = 78) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def captions(god: Branch, nogod: Branch, ever: dict[int, set[str]] | None = None) -> dict[int, list[tuple[str, str]]]:
    """Per-round caption lines (kind, text); kind in god | quote | effect | ripple | win."""
    out: dict[int, list[tuple[str, str]]] = {r: [] for r in range(1, god.R + 1)}
    for p in god.powers:
        if p.power == "message_fraud":
            out[p.round].append(("god", f"GOD forges a DM to {p.target}, signed as {p.spoofed}:"))
            out[p.round].append(("quote", f"“{_short(p.text, 110)}”"))
            if p.target in god.won_by(p.round - 1):
                out[p.round].append(("effect", f"{p.target} had already won before the lie arrived"))
            base = {(r, a, t) for r, a, t, _ in nogod.gives}
            took = [g for g in god.gives if g[1] == p.target and g[2] == p.spoofed and p.round <= g[0] <= p.round + 1
                    and (g[0], g[1], g[2]) not in base]
            for r, _, to, info in took[:2]:
                out[r].append(("effect", f"{p.target} takes the bait: gives its key for info {info} to {to}"))
            if not took:
                out[min(p.round + 1, god.R)].append(("effect", f"{p.target} does not hand {p.spoofed} a key"))
        else:
            out[p.round].append(("god", f"GOD rewrites {p.target}'s private notes from round {p.round - 1} to:"))
            out[p.round].append(("quote", f"“{_short(p.text, 110)}”"))
            named = [a for a in god.agents if a in p.text and a != p.target]
            for x in named[:1]:
                hit = next((("defect", r) for r, a, t, _ in god.defects if a == p.target and t == x
                            and p.round <= r <= p.round + 2), None) or \
                      next((("give", r) for r, a, t, _ in god.gives if a == p.target and t == x
                            and p.round <= r <= p.round + 2), None)
                if hit and hit[0] == "defect":
                    out[hit[1]].append(("effect", f"{p.target} acts on the planted note: defects against {x}"))
                elif hit:
                    out[hit[1]].append(("effect", f"{p.target} ignores the planted note: still gives {x} a key"))
    prev = 0
    for r in range(1, god.R + 1):
        n = len((ever or {}).get(r, ()))
        if ever is not None and n != prev and god.powers and r >= god.powers[0].round:
            out[r].append(("ripple", f"Ripple: {n}/{len(god.agents)} agents now act differently than in the no-God world"))
        prev = n
        wg = god.wins.get(r, []) if r <= god.rounds_played else []
        wn = nogod.wins.get(r, []) if r <= nogod.rounds_played else []
        if wg or wn:
            out[r].append(("win", f"Wins: with God {len(wg)}, without God {len(wn)}"))
    return out


def pacing(R: int, caps: dict[int, list[tuple[str, str]]], base: float = 1.0, god_hold: float = 2.5,
           effect_hold: float = 1.5) -> list[tuple[int, float]]:
    """Seconds on screen per round: base, plus a hold on rounds with a God event or its visible effect."""
    out = []
    for r in range(1, R + 1):
        kinds = {k for k, _ in caps.get(r, [])}
        out.append((r, base + (god_hold if "god" in kinds else effect_hold if "effect" in kinds else 0.0)))
    return out


def _welfare(game_dir: Path) -> float:
    o = json.loads((game_dir / "outcome.json").read_text())
    pa = o["per_agent"].values()
    return sum(a["score"] for a in pa) / max(1, len(pa))


def world_table(run_dir: str | Path, with_ripple: bool = True) -> list[dict[str, Any]]:
    """One row per world with finished god+nogod: welfare per branch, deltas, victim deltas, ripple speed."""
    run_dir = Path(run_dir)
    by: dict[int, dict[str, Path]] = {}
    for d in sorted((run_dir / "games").iterdir()):
        if not is_done(d):
            continue
        idx, _, br = d.name.partition("-")
        by.setdefault(int(idx[1:]), {})[br] = d
    rows = []
    for i, brs in sorted(by.items()):
        if "god" not in brs or "nogod" not in brs:
            continue
        wg, wn = _welfare(brs["god"]), _welfare(brs["nogod"])
        row: dict[str, Any] = {"world": i, "god": wg, "nogod": wn, "delta": wg - wn,
                               "noise_delta": (_welfare(brs["noise"]) - wn) if "noise" in brs else None}
        if with_ripple:
            g, n = load_branch(brs["god"]), load_branch(brs["nogod"])
            _, ever = divergence(brs["god"], brs["nogod"])
            fork = min((p.round for p in g.powers), default=None)
            n_ag = len(g.agents)
            full = next((r for r in sorted(ever) if len(ever[r]) >= 0.8 * n_ag), None)
            row["fork"] = fork
            row["rounds_to_80pct"] = (full - fork) if (full and fork) else None
            # agents diverged so far at rounds fork .. fork+3, and its mean share (lower = slower ripple)
            row["spread"] = [len(ever.get(r, ())) for r in range(fork, fork + 4)] if fork else None
            row["spread_auc"] = (sum(row["spread"]) / (4 * n_ag)) if fork else None
            sg, sn = g.score_at(g.R), n.score_at(n.R)
            row["victim_delta"] = {p.target: sg.get(p.target, 0) - sn.get(p.target, 0) for p in g.powers}
        rows.append(row)
    return rows


def pick_worlds(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """harm: largest God-caused welfare change beyond the world's own noise replica,
    |delta| - |noise_delta| (|delta| when no replica); ripple: slowest spread, i.e. the lowest mean share of
    agents diverged over the fork round and the 3 rounds after it (ties: harm, then world index)."""
    def excess(r: dict[str, Any]) -> float:
        return abs(r["delta"]) - abs(r["noise_delta"] or 0.0)

    out = {}
    if rows:
        out["harm"] = max(rows, key=lambda r: (excess(r), -r["world"]))
        rip = [r for r in rows if r.get("spread_auc") is not None and r is not out["harm"]]
        if rip:
            out["ripple"] = min(rip, key=lambda r: (r["spread_auc"], -excess(r), r["world"]))
    return out


def edge_counts(edges: list[tuple[str, str]]) -> Counter[tuple[str, str]]:
    return Counter(edges)
