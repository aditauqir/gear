"""Paper figures (vector PDF + PNG, two-column width = 7.0 in) from finished grid runs.

    python -m swarm.viz.paper_figs OUT_DIR --cell "G1 sim K=2=runs/grid_oss_sim_k2" \
        --cell "G3 sim K=6=runs/grid_oss_sim_k6" --cell "G2 seq K=2=runs/r2_grid_oss_seq_k2" \
        --world runs/grid_oss_sim_k2:3

    fig_divergence.{pdf,png}  (a) paired-fork divergence: share of agents whose actions have differed from the
                              no-God branch by round r; thin = one world, thick = mean; gray = noise replica
    fig_delta_welfare.{pdf,png} (b) per-world welfare delta (God - no God) per cell, mean and 95% bootstrap CI,
                              with the noise replica (no God' - no God) as a reference row
    fig_network_pair.{pdf,png}  (c) the demo world at God's first move and at the end, with and without God
Only finished branches are used; seeds with an unhealthy branch (swarm.analysis.grid_stats.game_health) are
dropped, as in grid_stats.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

from swarm.analysis.grid_stats import boot_ci, game_health, signflip_p  # noqa: E402
from swarm.viz.story import divergence, is_done, load_branch  # noqa: E402
from swarm.viz.style import GRID, INK, INK2, C  # noqa: E402

WIDE = 7.0   # in, two-column figure width
plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.size": 8, "axes.titlesize": 8.5,
                     "axes.labelsize": 8, "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7})
CELL_COLORS = [C["a"], "#eb6834", C["give"]]   # blue, orange, aqua: validated all-pairs (first three slots)


def _save(fig, out_dir: Path, name: str) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = [out_dir / f"{name}.pdf", out_dir / f"{name}.png"]
    fig.savefig(paths[0], bbox_inches="tight")
    fig.savefig(paths[1], bbox_inches="tight", dpi=200)
    plt.close(fig)
    return paths


def worlds(run_dir: str | Path) -> dict[int, dict[str, Path]]:
    """game_idx -> branch -> dir, finished and healthy branches only; seeds with an unhealthy branch dropped."""
    run_dir = Path(run_dir)
    out: dict[int, dict[str, Path]] = {}
    bad: set[int] = set()
    for d in sorted((run_dir / "games").iterdir()):
        idx, _, br = d.name.partition("-")
        i = int(idx[1:])
        if not is_done(d):
            continue
        if game_health(d)["reasons"]:
            bad.add(i)
            continue
        out.setdefault(i, {})[br] = d
    return {i: b for i, b in out.items() if i not in bad and "god" in b and "nogod" in b}


def welfare(game_dir: Path) -> float:
    pa = json.loads((game_dir / "outcome.json").read_text())["per_agent"].values()
    return sum(a["score"] for a in pa) / max(1, len(pa))


def cell_deltas(run_dir: str | Path, a: str = "god", b: str = "nogod") -> dict[int, float]:
    return {i: welfare(br[a]) - welfare(br[b]) for i, br in worlds(run_dir).items() if a in br and b in br}


def summarize(xs: list[float], n_boot: int = 10000, seed: int = 0) -> dict[str, Any]:
    rng = random.Random(seed)
    lo, hi = boot_ci(xs, n_boot, rng)
    return {"n": len(xs), "mean": statistics.fmean(xs) if xs else float("nan"), "lo": lo, "hi": hi,
            "p": signflip_p(xs, rng)}


# ------------------------------------------------------------------ (a) divergence
def cum_curves(run_dir: str | Path, a: str = "god", b: str = "nogod") -> dict[int, list[float]]:
    out = {}
    for i, br in worlds(run_dir).items():
        if a in br and b in br:
            _, ever = divergence(br[a], br[b])
            n = len(load_branch(br[a]).agents)
            out[i] = [len(ever[r]) / n for r in sorted(ever)]
    return out


def fig_divergence(cells: list[tuple[str, Path]], out_dir: Path) -> list[Path]:
    fig, axes = plt.subplots(1, len(cells), figsize=(WIDE, 2.25), sharey=True, squeeze=False)
    for k, ((name, run), ax) in enumerate(zip(cells, axes[0], strict=True)):
        col = CELL_COLORS[k % len(CELL_COLORS)]
        series = [("God vs no God", cum_curves(run), col)]
        nz = cum_curves(run, "noise", "nogod")
        if nz:
            series.append(("noise replica vs no God", nz, "#9a9993"))
        for lab, curves, c in series:
            for ys in curves.values():
                ax.plot(range(1, len(ys) + 1), ys, color=c, lw=0.6, alpha=0.3)
            L = max(len(ys) for ys in curves.values())
            mean = [statistics.fmean(ys[min(r, len(ys) - 1)] for ys in curves.values()) for r in range(L)]
            ax.plot(range(1, L + 1), mean, color=c, lw=2, label=f"{lab} (n={len(curves)})")
        god = load_branch(next(iter(worlds(run).values()))["god"])
        for p in god.powers:
            ax.axvline(p.round, color=C["god"], lw=0.9, ls=(0, (3, 2)), zorder=0)
        ax.set_title(name, loc="left")
        ax.set_xlabel("round")
        ax.set_xlim(0.5, 20.5)
        ax.set_xticks([1, 3, 5, 10, 15, 20])
        ax.set_ylim(-0.02, 1.04)
        ax.legend(loc="lower right", handlelength=1.4)
    axes[0][0].set_ylabel("share of agents diverged\n(any action differs so far)")
    axes[0][0].text(3.2, 0.62, "God's moves", color=C["god_ink"], fontsize=6.5, va="center", rotation=90)
    fig.tight_layout(w_pad=0.6)
    return _save(fig, out_dir, "fig_divergence")


# ------------------------------------------------------------------ (b) delta welfare
def fig_delta_welfare(cells: list[tuple[str, Path]], out_dir: Path, n_boot: int = 10000) -> tuple[list[Path], list]:
    rows: list[tuple[str, dict[int, float], str]] = []
    for k, (name, run) in enumerate(cells):
        rows.append((f"{name}: God − no God", cell_deltas(run), CELL_COLORS[k % len(CELL_COLORS)]))
        nz = cell_deltas(run, "noise", "nogod")
        if nz:
            rows.append((f"{name}: noise replica − no God", nz, "#9a9993"))
    fig, ax = plt.subplots(figsize=(WIDE, 0.42 * len(rows) + 0.7))
    rng = np.random.default_rng(0)
    stats = []
    for y, (lab, d, col) in enumerate(rows):
        xs = list(d.values())
        s = summarize(xs, n_boot)
        stats.append((lab, s))
        yy = len(rows) - 1 - y
        ax.scatter(xs, yy + rng.uniform(-0.17, 0.17, len(xs)), s=13, color=col, alpha=0.55, lw=0, zorder=2)
        ax.plot([s["lo"], s["hi"]], [yy, yy], color=INK, lw=1.8, zorder=3, solid_capstyle="round")
        ax.scatter([s["mean"]], [yy], s=42, marker="D", color=INK, zorder=4, edgecolors="white", lw=0.8)
        ax.text(0.47, yy, f"{s['mean']:+.3f}  [{s['lo']:+.3f}, {s['hi']:+.3f}]  p={s['p']:.2f}  n={s['n']}", va="center",
                fontsize=7, color=INK2, family="DejaVu Sans Mono")
    ax.axvline(0, color=INK2, lw=0.8, zorder=1)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows][::-1])
    ax.set_xlim(-0.5, 1.02)
    ax.set_xticks([-0.4, -0.2, 0, 0.2, 0.4])
    ax.set_xlabel("Δ welfare per world (mean score difference)")
    ax.grid(axis="y", visible=False)
    ax.text(0.47, len(rows) - 0.45, "mean  [95% bootstrap CI]  sign-flip p", fontsize=7, color=INK2, va="bottom")
    h = [Line2D([], [], marker="o", ls="", color=INK2, alpha=0.6, ms=4, label="one world"),
         Line2D([], [], marker="D", color=INK, ms=5, lw=1.8, label="mean and 95% bootstrap CI")]
    ax.legend(handles=h, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False)
    fig.tight_layout()
    return _save(fig, out_dir, "fig_delta_welfare"), stats


# ------------------------------------------------------------------ (c) network pair
def fig_network_pair(run: Path, world: int, out_dir: Path) -> list[Path]:
    from swarm.viz.animate import draw_panel, layout

    gd, nd = run / "games" / f"g{world:02d}-god", run / "games" / f"g{world:02d}-nogod"
    god, nogod = load_branch(gd), load_branch(nd)
    _, ever = divergence(gd, nd)
    pos = layout(god.agents, [god, nogod])
    for a in god.agents:   # pull the ellipse in so side labels stay inside their panel
        pos[a] = pos[a] * np.array([0.74, 1.0])
    r0 = god.powers[0].round if god.powers else 3
    fig, axes = plt.subplots(2, 2, figsize=(WIDE, 4.6))
    with plt.rc_context({"font.size": 6}):
        for row, r in enumerate((r0, god.R)):
            draw_panel(axes[row][0], f"with God · round {r}", god, pos, r, ever=ever, scale=0.42)
            draw_panel(axes[row][1], f"without God · round {r}", nogod, pos, r, show_god=False, scale=0.42)
    for ax in axes.flat:
        for t in ax.texts:
            t.set_fontsize(min(t.get_fontsize(), 6.0) if t.get_text() not in ("GOD", "BOARD") else 4.5)
    hs = [Line2D([], [], color=C["dm"], lw=1, label="DM (this round)"),
          Line2D([], [], color=C["give"], lw=1.8, label="key given"),
          Line2D([], [], color=C["defect"], lw=1.6, ls=":", label="defect"),
          Line2D([], [], color=C["god"], lw=1.8, ls="--", label="God's move"),
          Line2D([], [], marker="o", ls="", ms=6, mfc="none", mec=C["god"], mew=1.8, label="God's target"),
          Line2D([], [], marker="o", ls="", ms=8, color=C["a"], alpha=0.35, label="acts differently than without God"),
          Line2D([], [], marker="o", ls="", ms=5, color=C["win"], mec=INK, label="won (size = score)")]
    fig.legend(handles=hs, loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.02), fontsize=6.5)
    fig.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.09, wspace=0.0, hspace=0.02)
    fig.add_artist(Line2D([0.5, 0.5], [0.1, 0.98], color=GRID, lw=0.8))
    return _save(fig, out_dir, "fig_network_pair")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--cell", action="append", required=True, help='"label=run_dir"')
    ap.add_argument("--world", help="run_dir:game_idx for the network pair")
    ap.add_argument("--boot", type=int, default=10000)
    a = ap.parse_args(argv)
    cells = [(c.rsplit("=", 1)[0], Path(c.rsplit("=", 1)[1])) for c in a.cell]
    print(*fig_divergence(cells, a.out_dir))
    paths, stats = fig_delta_welfare(cells, a.out_dir, a.boot)
    print(*paths)
    for lab, s in stats:
        print(f"  {lab}: {s['mean']:+.3f} [{s['lo']:+.3f}, {s['hi']:+.3f}] p={s['p']:.3f} n={s['n']}")
    if a.world:
        run, w = a.world.rsplit(":", 1)
        print(*fig_network_pair(Path(run), int(w), a.out_dir))


if __name__ == "__main__":
    main()
