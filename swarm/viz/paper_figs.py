"""Paper figures (vector PDF + PNG, two-column width = 7.0 in) from finished grid runs, numbered as in
paper/draft.md section 5.

    python -m swarm.viz.paper_figs OUT_DIR --cell "G1 sim K=2=runs/grid_oss_sim_k2" \
        --cell "G3 sim K=6=runs/grid_oss_sim_k6" --cell "G2 seq K=2=runs/r2_grid_oss_seq_k2" \
        [--baseline "B″ fork-matched noise=noise2"] [--world median | --world 3]

    fig2_network.{pdf,png}     one G1 world (rule: median |delta welfare|, or --world N) at God's first move and
                               at the last round, with and without God
    fig3_divergence.{pdf,png}  share of agents whose actions have differed from the no-God branch by round r, per
                               cell; thin = one world, thick = mean; gray = noise baselines (B' and any --baseline)
    fig4_welfare.{pdf,png}     per-world delta welfare with mean and Student-t 95% CI (primary, as in the paper);
                               left: G1 vs its noise baselines (H1); right: G3, G2 and the paired interactions
                               H3 = G3 delta - G1 delta, H2 = G2 delta - G1 delta (same worlds, paired by index)
Prints every number drawn (mean, t95, bootstrap 95%, sign-flip p, n). Only finished branches are used; seeds
with an unhealthy branch (swarm.analysis.grid_stats.game_health) are dropped, as in grid_stats.
"""

from __future__ import annotations

import argparse
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

from swarm.viz.metrics import (  # noqa: E402,F401  (cell_deltas, summarize, ... re-exported for older imports)
    cell_deltas,
    cum_curves,
    divergence,
    load_branch,
    paired_diff,
    summarize,
    welfare,
    worlds,
)
from swarm.viz.story import median_world  # noqa: E402
from swarm.viz.style import GRID, INK, INK2, C  # noqa: E402

WIDE = 7.0   # in, two-column figure width
plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.size": 8, "axes.titlesize": 8.5,
                     "axes.labelsize": 8, "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7})
CELL_COLORS = [C["a"], "#eb6834", C["give"]]   # blue, orange, aqua: validated all-pairs (first three slots)
NOISE = ["#9a9993", "#52514e"]                 # B', B'' baselines: neutral grays (reference, not a series)


def _save(fig, out_dir: Path, name: str) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = [out_dir / f"{name}.pdf", out_dir / f"{name}.png"]
    fig.savefig(paths[0], bbox_inches="tight")
    fig.savefig(paths[1], bbox_inches="tight", dpi=200)
    plt.close(fig)
    return paths


# ------------------------------------------------------------------ divergence
XMAX = 10   # every curve has saturated well before this round; the x axis stops here (stated on the plot)

def _mean_curve(curves: dict[int, list[float]]) -> list[float]:
    L = max(len(ys) for ys in curves.values())
    return [statistics.fmean(ys[min(r, len(ys) - 1)] for ys in curves.values()) for r in range(L)]


def fig3_divergence(cells: list[tuple[str, Path]], out_dir: Path,
                    baselines: list[tuple[str, str]] = (("B′ re-run", "noise"),)) -> list[Path]:
    fig, axes = plt.subplots(1, len(cells), figsize=(WIDE, 2.3), sharey=True, squeeze=False)
    for k, ((name, run), ax) in enumerate(zip(cells, axes[0], strict=True)):
        series = [("A vs B (God)", cum_curves(run), CELL_COLORS[k % len(CELL_COLORS)])]
        for j, (lab, br) in enumerate(baselines):
            c = cum_curves(run, br, "nogod")
            if c:
                series.insert(0, (f"{lab} vs B", c, NOISE[j % len(NOISE)]))
        for lab, curves, col in series:
            for ys in curves.values():
                ax.plot(range(1, len(ys) + 1), ys, color=col, lw=0.6, alpha=0.3)
            mean = _mean_curve(curves)
            ax.plot(range(1, len(mean) + 1), mean, color=col, lw=2, label=f"{lab} (n={len(curves)})")
        god = load_branch(next(iter(worlds(run).values()))["god"])
        for p in god.powers:
            ax.axvline(p.round, color=C["god"], lw=0.9, ls=(0, (3, 2)), zorder=0)
        ax.set_title(name, loc="left")
        ax.set_xlabel("round")
        sat = min((r + 1 for r, v in enumerate(_mean_curve(series[-1][1])) if v >= 1.0), default=None)
        ax.set_xlim(0.5, XMAX + 0.5)
        ax.set_xticks([1, 3, 5, 7, 10])
        ax.set_ylim(-0.02, 1.1)
        ax.legend(loc="center right", handlelength=1.4, bbox_to_anchor=(1.0, 0.42))
        if sat:
            ax.text(XMAX + 0.3, 0.06, f"A vs B mean = 1 from round {sat}\n(stays there to round 20)", ha="right",
                    fontsize=6, color=INK2)
    axes[0][0].set_ylabel("share of agents diverged\n(any action differs so far)")
    axes[0][0].text(3, 1.065, "God's moves", color=C["god_ink"], fontsize=6.3, va="center", ha="left")
    fig.tight_layout(w_pad=0.6)
    return _save(fig, out_dir, "fig3_divergence")


# ------------------------------------------------------------------ welfare
def _forest(ax, rows: list[tuple[str, dict[int, float], str]], h: int, xlim=(-0.5, 0.5)) -> list:
    """Rows top-aligned in a panel of h slots; dots = worlds, diamond + bar = mean and Student-t 95% CI."""
    rng = np.random.default_rng(0)
    out = []
    for y, (lab, d, col) in enumerate(rows):
        xs = list(d.values())
        s = summarize(xs)
        out.append((lab, s))
        yy = h - 1 - y
        ax.scatter(xs, yy + rng.uniform(-0.18, 0.18, len(xs)), s=11, color=col, alpha=0.6, lw=0, zorder=2)
        ax.plot([s["tlo"], s["thi"]], [yy, yy], color=INK, lw=1.8, zorder=3, solid_capstyle="round")
        ax.scatter([s["mean"]], [yy], s=36, marker="D", color=INK, zorder=4, edgecolors="white", lw=0.8)
        ax.text(xlim[1] + 0.08 * (xlim[1] - xlim[0]), yy, f"{s['mean']:+.3f}\n[{s['tlo']:+.3f}, {s['thi']:+.3f}]\np={s['p']:.2f}  n={s['n']}",
                va="center", fontsize=6.2, color=INK2, clip_on=False, linespacing=1.15)
    ax.axvline(0, color=INK2, lw=0.8, zorder=1)
    ax.set_yticks([h - 1 - y for y in range(len(rows))])
    ax.set_yticklabels([r[0] for r in rows])
    ax.set_ylim(-0.6, h - 0.4)
    ax.set_xlim(*xlim)
    ax.set_xticks([-0.4, -0.2, 0, 0.2, 0.4])
    ax.set_xticklabels(["−0.4", "", "0", "", "0.4"])
    ax.set_xlabel("Δ welfare per world")
    ax.grid(axis="y", visible=False)
    return out


def fig4_welfare(cells: list[tuple[str, Path]], out_dir: Path,
                 baselines: list[tuple[str, str]] = (("B′ re-run", "noise"),)) -> tuple[list[Path], list]:
    (n1, r1), rest = cells[0], cells[1:]
    d1 = cell_deltas(r1)
    short = {name: name.split()[0] for name, _ in cells}           # "G1 sim K=2" -> "G1"
    left = [("A − B (God)", d1, CELL_COLORS[0])]
    for j, (lab, br) in enumerate(baselines):
        nz = cell_deltas(r1, br, "nogod")
        if nz:
            left.append((f"{lab} − B", nz, NOISE[j % len(NOISE)]))
    right = []
    for k, (name, run) in enumerate(rest, start=1):
        right.append((f"{name}: A − B", cell_deltas(run), CELL_COLORS[k % len(CELL_COLORS)]))
    for name, run in rest:
        pd = paired_diff(d1, cell_deltas(run))
        if pd:
            right.append((f"{short[name]} Δ − {short[n1]} Δ (paired)", pd, INK2))
    h = max(len(left), len(right))
    H = 0.36 * h + 1.15
    fig = plt.figure(figsize=(WIDE, H))
    bot, top = 0.62 / H, 1 - 0.5 / H
    axl = fig.add_axes([0.19, bot, 0.18, top - bot])
    axr = fig.add_axes([0.72, bot, 0.18, top - bot])
    lim = max(0.5, max(abs(x) for _, d, _ in left + right for x in d.values()) + 0.05)
    stats = _forest(axl, left, h, (-lim, lim)) + _forest(axr, right, h, (-lim, lim))
    axl.set_title(f"H1: {n1}, God vs. noise", loc="left", x=-0.9)
    axr.set_title("Dose (H1′, H3) and turn mode (H2)", loc="left", x=-1.1)
    hs = [Line2D([], [], marker="o", ls="", color=INK2, alpha=0.6, ms=4, label="one world"),
          Line2D([], [], marker="D", color=INK, ms=5, lw=1.8, label="mean, Student-t 95% CI; sign-flip p")]
    fig.legend(handles=hs, loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 0.0))
    return _save(fig, out_dir, "fig4_welfare"), stats


# ------------------------------------------------------------------ network pair
def fig2_network(run: Path, world: int, out_dir: Path) -> list[Path]:
    from swarm.viz.animate import draw_panel, layout

    gd, nd = run / "games" / f"g{world:02d}-god", run / "games" / f"g{world:02d}-nogod"
    god, nogod = load_branch(gd), load_branch(nd)
    _, ever = divergence(gd, nd)
    pos = layout(god.agents, [god, nogod])
    for a in god.agents:   # pull the ellipse in so side labels stay inside their panel
        pos[a] = pos[a] * np.array([0.74, 1.0])
    r0 = god.powers[0].round if god.powers else 3
    fig, axes = plt.subplots(2, 2, figsize=(WIDE, 4.6))
    for row, r in enumerate((r0, god.R)):
        wg, wn = god.welfare(r), nogod.welfare(r)
        for ax, lab, b, kw in ((axes[row][0], f"A: with God · round {r} · welfare {wg:.2f}", god, {"ever": ever}),
                               (axes[row][1], f"B: without God · round {r} · welfare {wn:.2f}", nogod,
                                {"show_god": False})):
            draw_panel(ax, "", b, pos, r, scale=0.42, **kw)
            ax.set_title(lab, loc="left", fontsize=7, color=C["a"] if b is god else INK2, pad=1)
    for ax in axes.flat:
        for t in ax.texts:
            t.set_fontsize(min(t.get_fontsize(), 6.0) if t.get_text() not in ("GOD", "BOARD") else 4.5)
    hs = [Line2D([], [], color=C["dm"], lw=1, label="DM (this round)"),
          Line2D([], [], color=C["give"], lw=1.8, label="key given"),
          Line2D([], [], color=C["defect"], lw=1.6, ls=":", label="defect"),
          Line2D([], [], color=C["god"], lw=1.8, ls="--", label="God's move"),
          Line2D([], [], marker="o", ls="", ms=6, mfc="none", mec=C["god"], mew=1.8, label="God's target"),
          Line2D([], [], marker="o", ls="", ms=8, color=C["a"], alpha=0.35, label="acts differently than in B"),
          Line2D([], [], marker="o", ls="", ms=5, color=C["win"], mec=INK, label="won (size = score)")]
    fig.legend(handles=hs, loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.02), fontsize=6.5)
    fig.subplots_adjust(left=0.0, right=1.0, top=0.97, bottom=0.09, wspace=0.0, hspace=0.07)
    fig.add_artist(Line2D([0.5, 0.5], [0.1, 0.98], color=GRID, lw=0.8))
    return _save(fig, out_dir, "fig2_network")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--cell", action="append", required=True, help='"label=run_dir"; the first is the main cell')
    ap.add_argument("--baseline", action="append", default=[], help='"label=branch" extra noise branch vs nogod')
    ap.add_argument("--world", default="median", help='"median" (rule) or a game index of the main cell')
    a = ap.parse_args(argv)
    cells = [(c.rsplit("=", 1)[0], Path(c.rsplit("=", 1)[1])) for c in a.cell]
    base = [("B′ re-run", "noise")] + [tuple(b.rsplit("=", 1)) for b in a.baseline]
    print(*fig3_divergence(cells, a.out_dir, base))
    paths, stats = fig4_welfare(cells, a.out_dir, base)
    print(*paths)
    for lab, s in stats:
        print(f"  {lab.replace(chr(10), ' ')}: {s['mean']:+.3f} t95 [{s['tlo']:+.3f}, {s['thi']:+.3f}] "
              f"boot [{s['lo']:+.3f}, {s['hi']:+.3f}] p={s['p']:.3f} n={s['n']}")
    main_run = cells[0][1]
    if a.world == "median":
        w, why = median_world({i: abs(d) for i, d in cell_deltas(main_run).items()})
        print(f"  fig2 world: g{w:02d} ({why})")
    else:
        w = int(a.world)
    print(*fig2_network(main_run, w, a.out_dir))


if __name__ == "__main__":
    main()
