"""One-factor sweep statistics (plan/SWEEP_PLAN.md): paired God - noGod deltas per cell, extended metrics.

    python -m swarm.analysis.sweep_stats --json plan/figs/sweep_stats.json \
        runs/grid_oss_sim_k2 runs/sweep_start1 ... [--boot 10000] [--seeds 0-11]

Per run dir (one cell: run.seed 1, n_games seeds, paired fork god/nogod per seed), per healthy seed
(health and exclusion rules = grid_stats.load_run: >10% call errors, >30% error-noop turns, or
budget_exceeded drop the whole seed), the delta d_s = metric(god) - metric(nogod) for:
  welfare, win_rate, burned, lost, rounds   (grid_stats.game_metrics, from outcome.json)
  defects, defects_wrong, gives, board_posts, dms   (outcomes.game_summary, from events)
and the God-vs-control divergence (ripple, coarse action signatures): final_cum (fraction of agents
whose actions ever differed) and post_fork_mean_frac. Reported: mean, 95% percentile bootstrap CI
over seeds, exact sign-flip p (n <= 16), n. With --ref <run>: for each other run, the paired
difference of welfare deltas (run - ref) on shared seeds (same run.seed => same worlds).
--seeds a-b restricts every run to those game_idx (e.g. compare G1 on the sweep's seeds).
Reads only run dirs; no LLM, no network.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
from pathlib import Path
from typing import Any

from swarm.analysis.grid_stats import boot_ci, load_run, signflip_p
from swarm.analysis.outcomes import game_summary
from swarm.analysis.ripple import ripple
from swarm.runlog.trace import load_game

BASE = ("welfare", "win_rate", "burned", "lost", "rounds")
EXTRA = ("defects", "defects_wrong", "gives", "board_posts", "dms")
DIV = ("final_cum", "post_fork_mean_frac")


def per_agent(s: dict[str, Any], n: int) -> dict[str, float]:
    return {"defects": s["defects"] / n, "defects_wrong": s["defects_wrong"] / n, "gives": s["gives"] / n,
            "board_posts": s["board_posts"] / n, "dms": s["messages"] / n}


def cell_rows(run_dir: Path, seeds: set[int] | None) -> dict[str, Any]:
    run = load_run(run_dir)
    man = json.loads((run_dir / "manifest.json").read_text())
    dirs = {(int(g["game_idx"]), g["branch"]): run_dir / g["dir"] for g in man["games"]}
    rows: dict[int, dict[str, float]] = {}
    levels: dict[int, dict[str, dict[str, float]]] = {}
    for i, br in sorted(run["seeds"].items()):
        if seeds is not None and i not in seeds:
            continue
        if "god" not in br or "nogod" not in br:
            continue
        ga = load_game(dirs[(i, "god")], with_llm_calls=False, with_snapshots=True)
        gb = load_game(dirs[(i, "nogod")], with_llm_calls=False, with_snapshots=True)
        n = max(1, len(ga.agents))
        sa, sb = per_agent(game_summary(ga), n), per_agent(game_summary(gb), n)
        rs = ripple(ga, gb).summary()
        d = {m: br["god"][m] - br["nogod"][m] for m in BASE}
        d.update({m: sa[m] - sb[m] for m in EXTRA})
        d["final_cum"] = float(rs["final_cum"] or 0.0)
        d["post_fork_mean_frac"] = float(rs["post_fork_mean_frac"] or 0.0)
        d["fork_round"] = float(rs["fork_round"] or 0)
        rows[i] = d
        levels[i] = {"god": {**br["god"], **sa}, "nogod": {**br["nogod"], **sb}}
    return {"name": run_dir.name, "run_seed": run["run_seed"], "rows": rows, "levels": levels,
            "unhealthy": run["unhealthy"]}


def summarize(xs: list[float], n_boot: int, rng: random.Random) -> dict[str, Any]:
    if not xs:
        return {"n": 0}
    lo, hi = boot_ci(xs, n_boot, rng)
    return {"mean": statistics.fmean(xs), "lo": lo, "hi": hi, "p": signflip_p(xs, rng), "n": len(xs),
            "sd": statistics.pstdev(xs) if len(xs) > 1 else 0.0}


def parse_seeds(s: str | None) -> set[int] | None:
    if not s:
        return None
    out: set[int] = set()
    for part in s.split(","):
        a, _, b = part.partition("-")
        out |= set(range(int(a), int(b or a) + 1))
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("runs", nargs="+", type=Path)
    ap.add_argument("--boot", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--seeds", default=None, help="restrict to game_idx, e.g. 0-11")
    ap.add_argument("--ref", type=Path, default=None, help="reference run for paired delta differences")
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args(argv)
    rng = random.Random(args.seed)
    seeds = parse_seeds(args.seeds)
    out: dict[str, Any] = {}
    cells = {r.name: cell_rows(r, seeds) for r in args.runs}
    ref = cell_rows(args.ref, seeds) if args.ref else None
    for name, c in cells.items():
        res: dict[str, Any] = {"unhealthy": c["unhealthy"], "seeds": sorted(c["rows"])}
        print(f"== {name} (n={len(c['rows'])} paired seeds)")
        for u in c["unhealthy"]:
            print(f"  UNHEALTHY {u} -> seed excluded")
        for m in (*BASE, *EXTRA, *DIV):
            xs = [r[m] for r in c["rows"].values()]
            s = summarize(xs, args.boot, rng)
            res[m] = s
            if s["n"]:
                print(f"  {m:20s} {s['mean']:+.3f} [{s['lo']:+.3f}, {s['hi']:+.3f}] p={s['p']:.3f} n={s['n']}")
        for br in ("god", "nogod"):
            for m in ("welfare", "win_rate"):
                xs = [lv[br][m] for lv in c["levels"].values()]
                res[f"{br}_{m}"] = statistics.fmean(xs) if xs else None
        if ref is not None and name != ref["name"] and ref["run_seed"] == c["run_seed"]:
            shared = sorted(set(ref["rows"]) & set(c["rows"]))
            diff = [c["rows"][i]["welfare"] - ref["rows"][i]["welfare"] for i in shared]
            res["vs_ref_welfare"] = summarize(diff, args.boot, rng)
            if diff:
                s = res["vs_ref_welfare"]
                print(f"  dwelfare - ref({ref['name']}) {s['mean']:+.3f} [{s['lo']:+.3f}, {s['hi']:+.3f}] "
                      f"p={s['p']:.3f} n={s['n']}")
        out[name] = res
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
