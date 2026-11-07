"""Sweep figures (plan/SWEEP_RESULTS.md): per factor, paired delta (God - noGod) vs the factor value,
mean with 95% bootstrap CI and n under each point. Reads the sweep_stats JSON.

    python infra/sweep/plot.py plan/figs/sweep_stats.json plan/figs

Blue = sweep cells; gray = existing grid cells at the base value (G1, G3) on the same seeds.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

BLUE, GRAY, INK, MUTED, SURF = "#2a78d6", "#8a8984", "#0b0b0b", "#52514e", "#fcfcfb"

# factor -> (x label, [(run name, x value, is_reference)])
FACTORS = {
    "start": ("God's first intervention round", [
        ("sweep_start1", 1, False), ("grid_oss_sim_k2", 3, True), ("sweep_start8", 8, False),
        ("sweep_start14", 14, False)]),
    "k": ("God budget K (interventions per game)", [
        ("sweep_k1", 1, False), ("grid_oss_sim_k2", 2, True), ("sweep_k4", 4, False),
        ("grid_oss_sim_k6", 6, True)]),
    "n": ("Number of agents N", [
        ("sweep_n5", 5, False), ("grid_oss_sim_k2", 10, True), ("sweep_n20", 20, False)]),
    "keys": ("Keys per agent", [
        ("sweep_keys3", 3, False), ("grid_oss_sim_k2", 5, True), ("sweep_keys8", 8, False)]),
    "rounds": ("Rounds per game", [
        ("grid_oss_sim_k2", 20, True), ("sweep_r40", 40, False)]),
}
METRICS = {"welfare": "Δ welfare (God − no-God)",
           "post_fork_mean_frac": "divergence: share of agents acting\ndifferently per round after the fork"}


def plot(stats: dict, factor: str, metric: str, out: Path) -> bool:
    xlabel, cells = FACTORS[factor]
    pts = [(x, ref, stats[name][metric], name) for name, x, ref in cells
           if name in stats and stats[name].get(metric, {}).get("n")]
    if not pts:
        return False
    fig, ax = plt.subplots(figsize=(5.2, 3.4), dpi=150, facecolor=SURF)
    ax.set_facecolor(SURF)
    ax.axhline(0, color=MUTED, lw=0.8, zorder=1)
    for x, ref, s, _ in pts:
        c = GRAY if ref else BLUE
        ax.plot([x, x], [s["lo"], s["hi"]], color=c, lw=2, solid_capstyle="round", zorder=2)
        ax.plot([x], [s["mean"]], "o", ms=8, color=c, mec=SURF, mew=2, zorder=3)
        ax.annotate(f"n={s['n']}", (x, s["lo"]), textcoords="offset points", xytext=(0, -12),
                    ha="center", fontsize=7, color=MUTED)
    ax.set_xticks([p[0] for p in pts])
    ax.set_xlabel(xlabel, color=INK, fontsize=9)
    ax.set_ylabel(METRICS[metric], color=INK, fontsize=8)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.grid(axis="y", color="#e6e5e0", lw=0.6, zorder=0)
    ax.set_title("blue = sweep cell, gray = existing grid cell; bars = 95% bootstrap CI",
                 fontsize=7, color=MUTED, loc="left")
    lo = min(p[2]["lo"] for p in pts)
    ax.set_ylim(top=max(p[2]["hi"] for p in pts) + 0.02, bottom=lo - 0.06 * max(0.2, abs(lo)) - 0.02)
    fig.tight_layout()
    fig.savefig(out, facecolor=SURF)
    plt.close(fig)
    return True


def main() -> None:
    stats = json.loads(Path(sys.argv[1]).read_text())
    outdir = Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    for f in FACTORS:
        for m in METRICS:
            p = outdir / f"sweep_{f}_{m}.png"
            if plot(stats, f, m, p):
                print(p)


if __name__ == "__main__":
    main()
