"""Paired God-effect statistics over grid run dirs (plan/GRID_PLAN.md).

    python -m swarm.analysis.grid_stats runs/<cell_run> [runs/<other_cell_run> ...] [--boot 10000]

Per run (one grid cell, n_games = seeds, paired fork god/nogod[/noise] per seed):
  per-seed delta d_s = metric(god) - metric(nogod); mean, 95% percentile bootstrap CI over seeds,
  two-sided sign-flip permutation p (exact for n <= 16, else 20000 random flips), and the noise
  floor (noise - nogod, from the B' replica) when the cell has one.
With two or more runs: the interaction (difference of mean deltas, run_i - run_0), bootstrapped by
resampling seed indices jointly when the runs share seeds (same run.seed and n_games => same worlds,
world_seed depends only on run.seed and game_idx), else independently.

Metrics (from games/*/outcome.json): welfare (mean score), win_rate, burned (needs burned by
others' defects, per agent), lost (needs lost to the wrong-defect penalty, per agent), rounds.
Health: a branch is UNHEALTHY when > 10% of its LLM calls errored, > 30% of its turns are noops
caused by an error (llm_error or failed parse), or its end_reason is budget_exceeded. Such
branches are listed and their whole seed is excluded from every delta (--keep-unhealthy keeps them).
Reads only run dirs; no LLM, no network.
"""

from __future__ import annotations

import argparse
import itertools
import json
import random
import statistics
from pathlib import Path
from typing import Any

METRICS = ("welfare", "win_rate", "burned", "lost", "rounds")


def game_metrics(game_dir: Path) -> dict[str, float]:
    out = json.loads((game_dir / "outcome.json").read_text())
    pa = out["per_agent"].values()
    n = max(1, len(pa))
    return {"welfare": sum(a["score"] for a in pa) / n,
            "win_rate": sum(1 for a in pa if a.get("won_round")) / n,
            "burned": sum(len(a.get("burned") or []) for a in pa) / n,
            "lost": sum(len(a.get("lost") or []) for a in pa) / n,
            "rounds": float(out["rounds_played"])}


def game_health(game_dir: Path) -> dict[str, Any]:
    """LLM error rate and error-caused noop rate of one branch; unhealthy -> reasons list non-empty."""
    calls = errs = 0
    with open(game_dir / "llm_calls.jsonl", encoding="utf-8") as f:
        for ln in f:
            calls += 1
            errs += '"error":null' not in ln.replace(" ", "")
    turns = noop_err = 0
    with open(game_dir / "events.jsonl", encoding="utf-8") as f:
        for ln in f:
            if '"type":"turn"' not in ln:
                continue
            td = json.loads(ln)["data"]
            turns += 1
            errored = (not td.get("parse_ok", True)
                       or any(str(e).startswith("llm_error") for e in td.get("errors") or []))
            noop_err += errored and all((a or {}).get("kind") == "noop" for a in td.get("actions") or [{}])
    out = json.loads((game_dir / "outcome.json").read_text())
    reasons = []
    if calls and errs / calls > 0.10:
        reasons.append(f"llm errors {errs}/{calls}")
    if turns and noop_err / turns > 0.30:
        reasons.append(f"error noops {noop_err}/{turns}")
    if out.get("end_reason") == "budget_exceeded":
        reasons.append("budget_exceeded")
    return {"calls": calls, "errors": errs, "turns": turns, "noop_err": noop_err, "reasons": reasons}


def load_run(run_dir: Path, keep_unhealthy: bool = False) -> dict[str, Any]:
    """-> {run_seed, seeds: {game_idx: {branch: metrics}}, unhealthy: [...]} from the manifest (done
    games only). A seed with any unhealthy branch is dropped unless keep_unhealthy."""
    man = json.loads((run_dir / "manifest.json").read_text())
    seeds: dict[int, dict[str, dict[str, float]]] = {}
    unhealthy: list[str] = []
    bad_seeds: set[int] = set()
    run_seed = None
    for g in man["games"]:
        if g.get("status") != "done":
            unhealthy.append(f"{g.get('dir')}: status {g.get('status')}")
            bad_seeds.add(int(g["game_idx"]))
            continue
        run_seed = g.get("run_seed", run_seed)
        h = game_health(run_dir / g["dir"])
        if h["reasons"]:
            unhealthy.append(f"{g['dir']}: {', '.join(h['reasons'])}")
            bad_seeds.add(int(g["game_idx"]))
        seeds.setdefault(int(g["game_idx"]), {})[g["branch"]] = game_metrics(run_dir / g["dir"])
    if not keep_unhealthy:
        for i in bad_seeds:
            seeds.pop(i, None)
    return {"name": run_dir.name, "run_seed": run_seed, "seeds": seeds, "unhealthy": unhealthy}


def deltas(run: dict[str, Any], metric: str, a: str = "god", b: str = "nogod") -> dict[int, float]:
    return {i: br[a][metric] - br[b][metric] for i, br in sorted(run["seeds"].items()) if a in br and b in br}


def boot_ci(xs: list[float], n_boot: int, rng: random.Random) -> tuple[float, float]:
    if len(xs) < 2:
        return (float("nan"), float("nan"))
    ms = sorted(statistics.fmean(rng.choices(xs, k=len(xs))) for _ in range(n_boot))
    return ms[int(0.025 * n_boot)], ms[int(0.975 * n_boot) - 1]


def signflip_p(xs: list[float], rng: random.Random) -> float:
    if not xs:
        return float("nan")
    obs = abs(sum(xs))
    if len(xs) <= 16:
        flips = itertools.product((1, -1), repeat=len(xs))
        tot = hit = 0
        for f in flips:
            tot += 1
            hit += abs(sum(s * x for s, x in zip(f, xs, strict=True))) >= obs - 1e-12
        return hit / tot
    hit = sum(abs(sum(x if rng.random() < 0.5 else -x for x in xs)) >= obs - 1e-12 for _ in range(20000))
    return (hit + 1) / 20001


def fmt(m: float, ci: tuple[float, float], p: float | None = None) -> str:
    s = f"{m:+.3f} [{ci[0]:+.3f}, {ci[1]:+.3f}]"
    return s + (f" p={p:.3f}" if p is not None else "")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("runs", nargs="+", type=Path)
    ap.add_argument("--boot", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--keep-unhealthy", action="store_true")
    args = ap.parse_args(argv)
    rng = random.Random(args.seed)
    runs = [load_run(r, args.keep_unhealthy) for r in args.runs]
    for run in runs:
        print(f"== {run['name']} (run.seed {run['run_seed']}, {len(run['seeds'])} seeds)")
        for u in run["unhealthy"]:
            print(f"  UNHEALTHY {u}" + ("" if args.keep_unhealthy else " -> seed excluded"))
        for m in METRICS:
            d = list(deltas(run, m).values())
            if not d:
                continue
            line = f"  {m:9s} god-nogod {fmt(statistics.fmean(d), boot_ci(d, args.boot, rng), signflip_p(d, rng))}"
            nz = list(deltas(run, m, "noise", "nogod").values())
            if nz:
                line += f" | noise-nogod {fmt(statistics.fmean(nz), boot_ci(nz, args.boot, rng))}"
                line += f" sd {statistics.pstdev(nz):.3f}"
            print(line + f" | sd(d) {statistics.pstdev(d):.3f} n={len(d)}")
    base = runs[0]
    for other in runs[1:]:
        print(f"== interaction: {other['name']} - {base['name']}")
        for m in METRICS:
            da, db = deltas(base, m), deltas(other, m)
            shared = sorted(set(da) & set(db)) if base["run_seed"] == other["run_seed"] else []
            if shared:
                diff = [db[i] - da[i] for i in shared]
                est = statistics.fmean(diff)
                ci = boot_ci(diff, args.boot, rng)
                print(f"  {m:9s} {fmt(est, ci, signflip_p(diff, rng))} (paired by seed, n={len(shared)})")
            elif da and db:
                xa, xb = list(da.values()), list(db.values())
                est = statistics.fmean(xb) - statistics.fmean(xa)
                bs = sorted(statistics.fmean(rng.choices(xb, k=len(xb))) - statistics.fmean(rng.choices(xa, k=len(xa)))
                            for _ in range(args.boot))
                print(f"  {m:9s} {fmt(est, (bs[int(.025 * args.boot)], bs[int(.975 * args.boot) - 1]))} (unpaired)")


if __name__ == "__main__":
    main()
