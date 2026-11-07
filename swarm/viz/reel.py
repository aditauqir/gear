"""Demo reel (~75 s): intro, two data-picked worlds from the main cell, the grid result, takeaways.

    python -m swarm.viz.reel demo/demo_reel.mp4 --main runs/grid_oss_sim_k2 \
        --cell "G3 sim K=6=runs/grid_oss_sim_k6" --cell "G2 seq K=2=runs/r2_grid_oss_seq_k2"

World picks come from swarm.viz.story.pick_worlds on the main cell (it has the noise replica):
  harm   = largest |delta welfare (God - no God)| - |delta welfare (noise replica - no God)|
  ripple = slowest spread of behavioural divergence to 80% of agents (ties: harm), excluding the harm pick
The picks and every number shown are written to OUT.json next to the video.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from swarm.viz.animate import FPS, Frames, WorldVideo, card_end, card_title, new_fig
from swarm.viz.paper_figs import CELL_COLORS, cell_deltas, cum_curves, summarize
from swarm.viz.story import pick_worlds, world_table
from swarm.viz.style import GRID, INK, INK2, C


def num(s: str) -> str:
    """Typographic minus for signed numbers shown on screen."""
    return re.sub(r"(?<![\w])-(?=\d)", "\u2212", s)


def card_section(fig, kicker: str, title: str, lines: list[str], size: float = 16) -> None:
    fig.clf()
    fig.add_artist(Line2D([0.08, 0.2], [0.66, 0.66], color=C["a"], lw=4))
    fig.text(0.08, 0.70, kicker, fontsize=15, color=C["a"], fontweight="bold")
    fig.text(0.08, 0.55, title, fontsize=30, fontweight="bold", color=INK)
    for i, ln in enumerate(lines):
        fig.text(0.08, 0.43 - i * 0.065, ln, fontsize=size, color=INK2)


def card_grid(fig, main: tuple[str, Path], cells: list[tuple[str, Path]], stats: dict) -> None:
    """Left: divergence over rounds (main cell, God vs no God, and noise replica). Right: delta welfare per cell."""
    fig.clf()
    fig.text(0.05, 0.92, "Across all worlds", fontsize=26, fontweight="bold", color=INK)
    fig.text(0.05, 0.86, "Behaviour diverges within ~2 rounds, but a God-free re-run diverges too. "
             "Welfare does not move beyond the noise.", fontsize=14, color=INK2)
    ax = fig.add_axes([0.06, 0.16, 0.36, 0.58])
    cur = cum_curves(main[1])
    nz = cum_curves(main[1], "noise", "nogod")
    for curves, col, lab in ((nz, "#9a9993", "re-run without God vs no God"), (cur, C["a"], "God vs no God")):
        if not curves:
            continue
        for ys in curves.values():
            ax.plot(range(1, len(ys) + 1), ys, color=col, lw=0.8, alpha=0.25)
        L = max(len(y) for y in curves.values())
        mean = [statistics.fmean(y[min(r, len(y) - 1)] for y in curves.values()) for r in range(L)]
        ax.plot(range(1, L + 1), mean, color=col, lw=3)
        ax.plot([], [], color=col, lw=3, label=lab)
    for r in (3, 5):
        ax.axvline(r, color=C["god"], lw=1.4, ls=(0, (3, 2)))
    ax.text(3.25, 0.62, "God's moves", rotation=90, color=C["god_ink"], fontsize=10)
    ax.legend(loc="lower right", fontsize=10.5, handlelength=1.6, title="mean (thin lines: single worlds)",
              title_fontsize=9.5)
    ax.set_xlim(0.5, 10.5)
    ax.set_ylim(-0.02, 1.05)
    ax.set_xticks([1, 3, 5, 7, 10])
    ax.text(10.3, 0.9, "(all stay at 1.0\nto round 20)", ha="right", fontsize=9.5, color=INK2)
    ax.tick_params(labelsize=10.5)
    ax.set_xlabel("round", fontsize=11)
    ax.set_title(f"Agents acting differently ({main[0]}, {len(cur)} worlds)", loc="left", fontsize=12.5,
                 color=INK, pad=10)
    ax2 = fig.add_axes([0.665, 0.16, 0.25, 0.58])
    rows = stats["rows"]
    for y, row in enumerate(rows):
        yy = len(rows) - 1 - y
        xs, s = row["deltas"], row["summary"]
        jit = [((i * 0.6180339) % 1 - 0.5) * 0.36 for i in range(len(xs))]
        ax2.scatter(xs, [yy + j for j in jit], s=30, color=row["color"], alpha=0.6, lw=0, zorder=2)
        ax2.plot([s["tlo"], s["thi"]], [yy, yy], color=INK, lw=3, zorder=3, solid_capstyle="round")
        ax2.scatter([s["mean"]], [yy], s=80, marker="D", color=INK, zorder=4, edgecolors="white", lw=1)
        ax2.text(0.5, yy, num(f"{s['mean']:+.2f}\n[{s['tlo']:+.2f}, {s['thi']:+.2f}]"), fontsize=10, va="center",
                 color=INK2)
    ax2.axvline(0, color=INK2, lw=1)
    ax2.set_yticks(range(len(rows)))
    ax2.set_yticklabels([r["label"] for r in rows][::-1], fontsize=10.5)
    ax2.set_xlim(-0.5, 0.62)
    ax2.set_xticks([-0.4, -0.2, 0, 0.2, 0.4])
    ax2.tick_params(labelsize=10.5)
    ax2.grid(axis="y", visible=False)
    ax2.set_xlabel("Δ welfare per world (dots); mean and 95% CI (t)", fontsize=11)
    ax2.set_title("Effect on welfare", loc="left", fontsize=12.5, color=INK, pad=10)
    fig.add_artist(Line2D([0.5, 0.5], [0.12, 0.78], color=GRID, lw=1))


def grid_stats(main: tuple[str, Path], cells: list[tuple[str, Path]], n_boot: int = 10000) -> dict:
    rows = []
    for k, (name, run) in enumerate([main] + cells):
        for a, b, lab, col in (("god", "nogod", f"{name}\nGod − no God", CELL_COLORS[k % len(CELL_COLORS)]),
                               ("noise", "nogod", f"{name}\nre-run, no God", "#9a9993")):
            d = cell_deltas(run, a, b)
            if d:
                rows.append({"label": lab, "kind": a, "name": name, "color": col, "deltas": list(d.values()),
                             "summary": summarize(list(d.values()), n_boot)})
    return {"rows": rows}


def build(out: Path, main: tuple[str, Path], cells: list[tuple[str, Path]], n_boot: int = 10000) -> dict:
    rows = world_table(main[1])
    picks = pick_worlds(rows)
    st = grid_stats(main, cells, n_boot)
    info = {"main": str(main[1]), "picks": {k: {kk: v for kk, v in r.items()} for k, r in picks.items()},
            "grid": [{"label": r["label"].replace("\n", " "), **{k: r["summary"][k] for k in ("n", "mean", "tlo", "thi", "lo", "hi", "p")}}
                     for r in st["rows"]]}
    g1 = st["rows"][0]["summary"]
    with tempfile.TemporaryDirectory() as td:
        fr = Frames(td)
        f = new_fig()
        card_title(f, "Here K=2: forged DM r3, notes r5.",
                   f"Shown: two worlds from {main[0]} ({len(rows)} worlds), picked from the data, then the grid result.")
        fr.add(f, 8.0)
        for key, kicker, title, why, upto, fast in (
                ("harm", "World 1 of 2", "The biggest God effect",
                 lambda r: [f"World g{r['world']:02d}: welfare {r['god']:.2f} with God vs {r['nogod']:.2f} without "
                            f"(Δ {r['delta']:+.2f}).",
                            f"Its noise replica (no God, re-sampled) differs by {r['noise_delta']:+.2f}:",
                            "the largest God effect beyond noise of all worlds."], None, 8),
                ("ripple", "World 2 of 2", "Watching behaviour diverge",
                 lambda r: [f"World g{r['world']:02d}: the slowest-spreading ripple of all {len(rows)} worlds.",
                            "Agents acting differently from the no-God world: "
                            + " → ".join(f"{n} (r{r['fork'] + i})" for i, n in enumerate(r["spread"])) + ".",
                            f"Final Δ welfare {r['delta']:+.2f}: behaviour changed, outcome barely did."], 8, None)):
            if key not in picks:
                continue
            r = picks[key]
            card_section(f, kicker, title, [num(x) for x in why(r)])
            fr.add(f, 5.0)
            plt.close(f)
            g = f"g{r['world']:02d}"
            wv = WorldVideo(main[1] / "games" / f"{g}-god", main[1] / "games" / f"{g}-nogod",
                            f"{main[0]} · world {g} · 10 agents · gpt-oss-120b")
            wv.frames(fr, upto=upto, fast_after=fast)
            plt.close(wv.fig)
            f = new_fig()
            if upto is None:
                card_end(f, wv.god, wv.nogod, "")
                fr.add(f, 4.5)
        f = new_fig()
        card_grid(f, main, cells, st)
        fr.add(f, 9.0)
        nz = next((r for r in st["rows"] if r["kind"] == "noise"), None)
        others = [r for r in st["rows"][1:] if r["kind"] == "god"]
        lines = ["• After God's forged DM, every agent acts differently within ~2 rounds.",
                 "• But a God-free re-run diverges just as completely: divergence alone is not God's ripple.",
                 f"• Welfare effect of a K=2 God: {g1['mean']:+.2f} [{g1['tlo']:+.2f}, {g1['thi']:+.2f}] "
                 f"(n={g1['n']}): indistinguishable from zero."]
        if nz:
            lines.append(f"• A God-free re-run of one world moves welfare by up to "
                         f"{max(abs(x) for x in nz['deltas']):.2f}: single worlds are anecdotes.")
        if others:
            lines.insert(3, "• " + ";  ".join(f"{r['name']}: {r['summary']['mean']:+.2f} "
                                           f"[{r['summary']['tlo']:+.2f}, {r['summary']['thi']:+.2f}]" for r in others))
        card_section(f, "Takeaways", "Trajectories diverge; outcomes don't", [num(x) for x in lines], size=14.5)
        fr.add(f, 8.0)
        plt.close(f)
        info["seconds"] = fr.n / FPS
        fr.encode(out, crf=27)
    out.with_suffix(".json").write_text(json.dumps(info, indent=1, default=float))
    return info


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("--main", type=Path, required=True)
    ap.add_argument("--main-label", default="K=2, sim turns")
    ap.add_argument("--cell", action="append", default=[], help='"label=run_dir"')
    ap.add_argument("--boot", type=int, default=10000)
    a = ap.parse_args(argv)
    cells = [(c.rsplit("=", 1)[0], Path(c.rsplit("=", 1)[1])) for c in a.cell]
    info = build(a.out, (a.main_label, a.main), cells, a.boot)
    print(json.dumps({"seconds": info["seconds"], "picks": {k: v["world"] for k, v in info["picks"].items()}}))


if __name__ == "__main__":
    main()
