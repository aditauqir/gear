"""Results dashboard: one self-contained HTML page (inline CSS + inline SVG charts, no network) for grid/sweep cells.

    python -m swarm.viz.dashboard plan/figs/grid_dashboard.html \
        --cell "G1 sim K=2=runs/grid_oss_sim_k2" --cell "G3 sim K=6=runs/grid_oss_sim_k6" \
        --cell "G2 seq K=2=runs/r2_grid_oss_seq_k2" [--sweeps "runs/sweep_*"] [--per-run]

Every number is computed from the run logs through swarm.viz.metrics (nothing typed by hand):
  per cell   config digest, status (done/running), Δ = God − no-God per world for every outcome metric with
             mean, Student-t 95% CI (primary), sign-flip p, n, sd, MDE (80% power) and percentile bootstrap,
             the noise baseline (re-run without God − no-God) next to it, God vs noise per world, outcome
             distributions, divergence curves aligned on each branch's fork round, LLM health and cost
  across     paired contrasts of each cell's Δ against the first cell (same worlds when run.seed matches)
Cells with no finished God/no-God pair are listed as skipped; partially finished cells use finished worlds only
and are flagged. Re-run any time; it only reads runs/.
"""

from __future__ import annotations

import argparse
import glob
import html
import io
import re
import statistics
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from swarm.viz.metrics import (  # noqa: E402
    GAME_METRICS,
    PAIR_METRICS,
    branch_values,
    cell_round_means,
    deltas,
    load_cell,
    paired_or_unpaired,
    summarize,
)
from swarm.viz.style import GRID, INK, INK2, C  # noqa: E402

NOISE_COL = "#9a9993"
CELL_COLORS = [C["a"], "#eb6834", C["give"]]
TABLE_METRICS = ["welfare", "win_rate", "lost", "burned", "gives", "defects_ok", "board_posts", "dms", "rounds",
                 "div_post_fork", "div_final_cum"]
N_BOOT = 10000


# ------------------------------------------------------------------ formatting
def num(x: float | None, d: int = 3, sign: bool = True) -> str:
    if x is None or x != x:
        return "–"
    s = f"{x:+.{d}f}" if sign else f"{x:.{d}f}"
    return s.replace("-", "−")


def ci(lo: float, hi: float, d: int = 3) -> str:
    return f"[{num(lo, d)}, {num(hi, d)}]"


def pcls(p: float) -> str:
    return "sig" if p == p and p < 0.05 else ""


def pcell(p: float, pair: bool = False, cls: str = "") -> str:
    """Divergence is measured against an all-zero reference, so its p is not a test of God: shown greyed."""
    if pair:
        return f"<td class='dim {cls}' title='measured against 0; compare with the re-run row'>({p:.3f})</td>"
    return f"<td class='{cls} {pcls(p)}'>{p:.3f}</td>"


def schedule(cf: dict[str, Any]) -> str:
    """'message_fraud@r3, cot_control@r5' -> 'fraud r3 · notes r5' (compact)."""
    by: dict[str, list[str]] = {}
    for x in cf.get("schedule") or []:
        pw, _, r = x.partition("@r")
        by.setdefault("fraud" if "fraud" in pw else "notes" if "cot" in pw else pw, []).append(r)
    return " · ".join(f"{k} r{','.join(v)}" for k, v in by.items()) or "–"


def svg(fig) -> str:
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight")
    plt.close(fig)
    s = buf.getvalue()
    s = re.sub(r"<metadata>.*?</metadata>", "", s[s.index("<svg"):], flags=re.S)
    return s


# ------------------------------------------------------------------ charts
def chart_god_vs_noise(cell: dict[str, Any]) -> str:
    """Per world: Δwelfare of God (blue) and of the God-free re-run (gray), on one row per world."""
    dg = deltas(cell, "welfare", "god")
    dn = deltas(cell, "welfare", "noise")
    ws = sorted(dg)
    fig, ax = plt.subplots(figsize=(5.2, 0.24 * len(ws) + 1.0))
    for y, i in enumerate(ws):
        xs = [dg[i]] + ([dn[i]] if i in dn else [])
        ax.plot([min(xs), max(xs)], [y, y], color=GRID, lw=3, zorder=1, solid_capstyle="round")
        if i in dn:
            ax.scatter([dn[i]], [y], s=34, facecolors="none", edgecolors=INK2, lw=1.6, zorder=2,
                       label="re-run without God − no God" if y == 0 else None)
        ax.scatter([dg[i]], [y], s=30, color=C["a"], zorder=3, label="God − no God" if y == 0 else None)
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_yticks(range(len(ws)))
    ax.set_yticklabels([f"g{i:02d}" for i in ws], fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("Δ welfare in this world", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.grid(axis="y", visible=False)
    ax.legend(fontsize=7, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False)
    return svg(fig)


def chart_distributions(cell: dict[str, Any], metric: str = "welfare") -> str:
    brs = [b for b in ("nogod", "god", "noise") if branch_values(cell, metric, b)]
    lab = {"nogod": "no God", "god": "with God", "noise": "re-run, no God"}
    col = {"nogod": C["b"], "god": C["a"], "noise": NOISE_COL}
    fig, ax = plt.subplots(figsize=(4.2, 0.55 * len(brs) + 0.9))
    rng = np.random.default_rng(0)
    for y, b in enumerate(brs):
        xs = list(branch_values(cell, metric, b).values())
        ax.scatter(xs, y + rng.uniform(-0.16, 0.16, len(xs)), s=16, color=col[b], alpha=0.75, lw=0, zorder=2)
        q1, med, q3 = np.percentile(xs, [25, 50, 75])
        ax.plot([q1, q3], [y, y], color=INK, lw=4, alpha=0.25, solid_capstyle="butt", zorder=1)
        ax.plot([med, med], [y - 0.25, y + 0.25], color=INK, lw=1.6, zorder=3)
    ax.set_yticks(range(len(brs)))
    ax.set_yticklabels([lab[b] for b in brs], fontsize=7.5)
    ax.set_xlabel(f"{GAME_METRICS[metric][0]} per world (bar = median, band = IQR)", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.grid(axis="y", visible=False)
    return svg(fig)


def chart_divergence(cell: dict[str, Any]) -> str:
    """Share of agents diverged from no-God vs rounds since the branch forked (God: its first move; re-run:
    its first differing round)."""
    fig, ax = plt.subplots(figsize=(4.6, 2.3))
    for br, col, lab in (("noise", NOISE_COL, "re-run without God"), ("god", C["a"], "with God")):
        curves = []
        forks = []
        for w in cell["worlds"].values():
            p = w["pairs"].get(br)
            if p and p["fork"]:
                c = p["curve"][p["fork"] - 1:]
                curves.append(c)
                forks.append(p["fork"])
                ax.plot(range(len(c)), c, color=col, lw=0.6, alpha=0.25)
        if curves:
            L = max(len(c) for c in curves)
            mean = [statistics.fmean(c[min(k, len(c) - 1)] for c in curves) for k in range(L)]
            fk = statistics.median(forks)
            ax.plot(range(L), mean, color=col, lw=2.2, label=f"{lab} (forks at r{fk:g}, n={len(curves)})")
    ax.set_xlim(-0.3, 8.3)
    ax.set_ylim(-0.02, 1.05)
    ax.set_xlabel("rounds since the branch forked", fontsize=8)
    ax.set_ylabel("share of agents diverged", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.legend(fontsize=7, loc="lower right")
    return svg(fig)


def chart_trajectories(run_dir: str | Path) -> str:
    """Mean per-round trajectories (welfare, winners, keys given, defects) per branch, averaged over worlds."""
    m = cell_round_means(run_dir)
    lab = {"nogod": "no God", "god": "with God", "noise": "re-run, no God"}
    col = {"nogod": C["b"], "god": C["a"], "noise": NOISE_COL}
    fields = [("welfare", "welfare"), ("winners", "winners"), ("gives", "keys given (cum.)"),
              ("defects", "defects (cum.)")]
    fig, axes = plt.subplots(1, 4, figsize=(9.6, 2.0))
    for ax, (f, t) in zip(axes, fields, strict=True):
        for br in ("noise", "nogod", "god"):
            if br in m:
                ys = m[br][f]
                ax.plot(range(len(ys)), ys, color=col[br], lw=1.8 if br == "god" else 1.4,
                        ls="--" if br == "noise" else "-", label=lab[br])
        ax.set_title(t, fontsize=8.5, loc="left")
        ax.tick_params(labelsize=7)
        ax.set_xlabel("round", fontsize=7.5)
    axes[0].legend(fontsize=7, loc="lower right")
    fig.tight_layout(w_pad=1.0)
    return svg(fig)


def chart_overview(cells: list[tuple[str, dict[str, Any]]]) -> str:
    """Δwelfare per world for every cell (dots) with mean and t95, noise baselines as gray rows."""
    rows = []
    for k, (lab, c) in enumerate(cells):
        rows.append((f"{lab}: God − no God", deltas(c, "welfare", "god"), CELL_COLORS[k % 3]))
        dn = deltas(c, "welfare", "noise")
        if dn:
            rows.append((f"{lab}: re-run − no God", dn, NOISE_COL))
    rows = [r for r in rows if r[1]]
    fig, ax = plt.subplots(figsize=(6.4, 0.36 * len(rows) + 0.8))
    rng = np.random.default_rng(0)
    for y, (_lab, d, col) in enumerate(rows):
        xs = list(d.values())
        s = summarize(xs, 500)
        ax.scatter(xs, y + rng.uniform(-0.15, 0.15, len(xs)), s=13, color=col, alpha=0.65, lw=0, zorder=2)
        if s["n"] > 1:
            ax.plot([s["tlo"], s["thi"]], [y, y], color=INK, lw=1.8, zorder=3)
        ax.scatter([s["mean"]], [y], marker="D", s=30, color=INK, edgecolors="white", lw=0.8, zorder=4)
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows], fontsize=7.5)
    ax.invert_yaxis()
    ax.set_xlabel("Δ welfare per world; ◆ mean with Student-t 95% CI", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.grid(axis="y", visible=False)
    return svg(fig)


# ------------------------------------------------------------------ tables
def stats_row(xs: dict[int, float]) -> dict[str, Any] | None:
    return summarize(list(xs.values()), N_BOOT) if xs else None


def effect_table(cell: dict[str, Any]) -> str:
    has_noise = any("noise" in w["branches"] for w in cell["worlds"].values())
    head = ("<tr><th>metric</th><th>with God</th><th>no God</th><th>Δ God − no God</th><th>95% t-CI</th>"
            "<th>p</th><th>n</th><th>sd</th><th>MDE</th>"
            + ("<th class=noise>Δ re-run − no God</th><th class=noise>95% t-CI</th><th class=noise>p</th>"
               if has_noise else "") + "</tr>")
    out = [head]
    for m in TABLE_METRICS:
        lab, desc = GAME_METRICS.get(m) or PAIR_METRICS[m]
        s = stats_row(deltas(cell, m, "god"))
        if not s:
            continue
        pair = m in PAIR_METRICS
        g = branch_values(cell, m, "god") if not pair else {}
        n_ = branch_values(cell, m, "nogod") if not pair else {}
        mg = num(statistics.fmean(g.values()), 3, False) if g else "–"
        mn = num(statistics.fmean(n_.values()), 3, False) if n_ else ("0 (ref.)" if pair else "–")
        cells = [f'<td title="{html.escape(desc)}">{html.escape(lab)}</td>', f"<td>{mg}</td>", f"<td>{mn}</td>",
                 f"<td><b>{num(s['mean'])}</b></td>",
                 f"<td title='percentile bootstrap 95%: {ci(s['lo'], s['hi'])}'>{ci(s['tlo'], s['thi'])}</td>",
                 pcell(s["p"], pair), f"<td>{s['n']}</td>",
                 f"<td>{num(s['sd'], 3, False)}</td>", f"<td>{num(s['mde'], 3, False) if not pair else '–'}</td>"]
        if has_noise:
            z = stats_row(deltas(cell, m, "noise"))
            cells += ([f"<td class=noise>{num(z['mean'])}</td>", f"<td class=noise>{ci(z['tlo'], z['thi'])}</td>",
                       pcell(z["p"], pair, "noise")] if z else ["<td>–</td>"] * 3)
        out.append("<tr>" + "".join(cells) + "</tr>")
    return "<div class=tbl><table>" + "".join(out) + "</table></div>"


def health_table(cell: dict[str, Any]) -> str:
    keys = [("branches", "branches"), ("calls", "LLM calls"), ("paid", "paid"), ("cache_hits", "cache hits"),
            ("errors", "errors"), ("http_retries", "HTTP retries"), ("parse_retries", "parse retries"),
            ("parse_failures", "parse failures (turns)"), ("truncated", "finish=length"),
            ("cheap", "calls at cheapest price"), ("cost_usd", "cost (USD)"), ("tok", "tokens in / out"),
            ("lat", "latency p50 / p90 (s)")]
    cols = sorted(cell["health"], key=lambda b: ("god", "nogod", "noise").index(b) if b in ("god", "nogod", "noise") else 9)
    allh = [h for b in cols for h in cell["health"][b]]

    def agg(hs: list[dict[str, Any]], k: str) -> str:
        if not hs:
            return "–"
        if k == "branches":
            return str(len(hs))
        if k == "cost_usd":
            return f"${sum(h['cost_usd'] for h in hs):.4f}"
        if k == "tok":
            return f"{sum(h['prompt_tokens'] for h in hs) / 1e6:.2f}M / {sum(h['completion_tokens'] for h in hs) / 1e6:.2f}M"
        if k == "lat":
            p50 = [h["latency_p50"] for h in hs if h["latency_p50"] is not None]
            p90 = [h["latency_p90"] for h in hs if h["latency_p90"] is not None]
            return f"{statistics.median(p50):.1f} / {statistics.median(p90):.1f}" if p50 else "–"
        if k == "cheap":
            a, b = sum(h["price_cheapest"] for h in hs), sum(h["price_fallback"] for h in hs)
            return f"{100 * a / (a + b):.0f}%" if a + b else "–"
        v = sum(h[k] for h in hs)
        base = sum(h["turns"] for h in hs) if k == "parse_failures" else sum(h["calls"] for h in hs)
        return f"{v}" + (f" ({100 * v / base:.2f}%)" if k in ("errors", "parse_retries", "parse_failures", "truncated")
                         and base else "")

    head = "<tr><th></th>" + "".join(f"<th>{html.escape(b)}</th>" for b in cols) + "<th>all</th></tr>"
    rows = [head] + ["<tr><td>" + lab + "</td>" + "".join(f"<td>{agg(cell['health'][b], k)}</td>" for b in cols)
                     + f"<td><b>{agg(allh, k)}</b></td></tr>" for k, lab in keys]
    return "<div class=tbl><table>" + "".join(rows) + "</table></div>"


def world_table(cell: dict[str, Any]) -> str:
    brs = [b for b in ("god", "nogod", "noise") if any(b in w["branches"] for w in cell["worlds"].values())]
    head = ("<tr><th>world</th>" + "".join(f"<th>welfare {b}</th>" for b in brs) + "<th>Δ God</th>"
            + ("<th>Δ re-run</th>" if "noise" in brs else "") + "<th>wins God / no God</th>"
            "<th>div. post-fork</th><th>God fork</th></tr>")
    rows = [head]
    for i, w in sorted(cell["worlds"].items()):
        b = w["branches"]
        r = [f"<td>g{i:02d}</td>"] + [f"<td>{num(b[x]['welfare'], 2, False) if x in b else '–'}</td>" for x in brs]
        r.append(f"<td><b>{num(b['god']['welfare'] - b['nogod']['welfare'], 2)}</b></td>")
        if "noise" in brs:
            r.append(f"<td class=noise>{num(b['noise']['welfare'] - b['nogod']['welfare'], 2) if 'noise' in b else '–'}</td>")
        r.append(f"<td>{b['god']['win_rate']:.1f} / {b['nogod']['win_rate']:.1f}</td>")
        pg = w["pairs"].get("god") or {}
        r.append(f"<td>{num(pg.get('div_post_fork'), 2, False)}</td><td>r{pg.get('fork') or '–'}</td>")
        rows.append("<tr>" + "".join(r) + "</tr>")
    return "<details><summary>Per-world table</summary><div class=tbl><table>" + "".join(rows) + "</table></div></details>"


def overview_table(cells: list[tuple[str, dict[str, Any]]]) -> str:
    head = ("<tr><th>cell</th><th>N</th><th>rounds</th><th>turns</th><th>God</th>"
            "<th>worlds used</th><th>Δ welfare [95% t-CI]</th><th>p</th>"
            "<th>re-run − no God</th><th>MDE</th><th>cost</th></tr>")
    rows = [head]
    for lab, c in cells:
        cf = c["config"]
        s = stats_row(deltas(c, "welfare", "god"))
        z = stats_row(deltas(c, "welfare", "noise"))
        cost = sum(h["cost_usd"] for hs in c["health"].values() for h in hs)
        partial = len(c["worlds"]) < c["n_worlds_total"]
        st = ", ".join(f"{v} {k}" for k, v in sorted(c["status"].items()))
        rows.append(
            f"<tr><td title='{html.escape(c['path'])}'><b>{html.escape(lab)}</b></td>"
            f"<td>{cf.get('n_agents', '–')}</td><td>{cf.get('max_rounds', '–')}</td><td>{cf.get('turn_mode', '–')}</td>"
            f"<td>K={cf.get('god_k', '–')}: {html.escape(schedule(cf))}</td>"
            f"<td title='branches: {html.escape(st)}'>{len(c['worlds'])} / {c['n_worlds_total']}"
            f"{' <span class=tag>partial</span>' if partial else ''}</td>"
            f"<td><b>{num(s['mean'])}</b> {ci(s['tlo'], s['thi'])}</td><td class='{pcls(s['p'])}'>{s['p']:.3f}</td>"
            f"<td class=noise>{(num(z['mean']) + ' ' + ci(z['tlo'], z['thi'])) if z else '–'}</td>"
            f"<td>{num(s['mde'], 3, False)}</td><td>${cost:.3f}</td></tr>")
    return "<div class=tbl><table>" + "".join(rows) + "</table></div>"


def contrast_table(cells: list[tuple[str, dict[str, Any]]]) -> str:
    """Each cell's God effect minus the reference (first) cell's: paired by world when both cells played the
    identical worlds (same world_hash), else unpaired (Welch t CI, no p)."""
    if len(cells) < 2:
        return ""
    (l0, c0) = cells[0]
    head = ("<tr><th>contrast</th><th>metric</th><th>pairing</th><th>Δ of Δ</th><th>95% t-CI</th><th>p</th>"
            "<th>n</th></tr>")
    rows = [head]
    for lab, c in cells[1:]:
        for m in ("welfare", "win_rate", "lost", "gives", "defects_ok"):
            kind, s = paired_or_unpaired(c0, c, m)
            if not s:
                continue
            p = f"<td class='{pcls(s['p'])}'>{s['p']:.3f}</td>" if s["p"] == s["p"] else "<td class=dim>–</td>"
            rows.append(f"<tr><td>{html.escape(lab)} − {html.escape(l0)}</td><td>{GAME_METRICS[m][0]}</td>"
                        f"<td class=dim>{kind}</td><td><b>{num(s['mean'])}</b></td><td>{ci(s['tlo'], s['thi'])}</td>"
                        f"{p}<td>{s['n']}</td></tr>")
    return "<div class=tbl><table>" + "".join(rows) + "</table></div>" if len(rows) > 1 else ""


# ------------------------------------------------------------------ page
CSS = """
:root{--bg:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--line:#e4e3df;--accent:#2a78d6;--god:#c4386f;--sig:#c4386f}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#0d0d0d;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--line:#383835;--accent:#3987e5;--god:#e87ba4;--sig:#e87ba4}}
:root[data-theme="dark"]{--bg:#0d0d0d;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--line:#383835;--accent:#3987e5;--god:#e87ba4;--sig:#e87ba4}
*{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1240px;margin:0 auto;padding:24px 16px 64px} h1{font-size:24px;margin:0 0 4px}
h2{font-size:18px;margin:40px 0 10px;padding-top:10px;border-top:1px solid var(--line)} h3{font-size:14px;margin:20px 0 6px;color:var(--ink2)}
.sub,.dim{color:var(--ink2)} nav a{color:var(--accent);margin-right:14px;text-decoration:none}
.tbl{overflow-x:auto;background:var(--surface);border:1px solid var(--line);border-radius:8px;margin:8px 0}
table{border-collapse:collapse;width:100%;font-size:12px;font-variant-numeric:tabular-nums}
th,td{padding:4px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap} th:first-child,td:first-child{text-align:left}
th{color:var(--ink2);font-weight:600} td.noise,th.noise{color:var(--ink2);background:color-mix(in srgb,var(--line) 35%,transparent)}
td.sig{color:var(--sig);font-weight:700}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(380px,1fr));gap:12px;align-items:start}
.fig{background:#fcfcfb;border:1px solid var(--line);border-radius:8px;padding:8px} .fig svg{width:100%;height:auto;display:block}
.fig .cap{color:#52514e;font-size:12px;margin:4px 2px 0}
.kpis{display:flex;flex-wrap:wrap;gap:12px;margin:14px 0}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:10px 14px;min-width:200px}
.kpi b{display:block;font-size:22px;font-variant-numeric:tabular-nums} .kpi span{color:var(--ink2);font-size:12px}
.tag{display:inline-block;padding:0 6px;border-radius:4px;font-size:11px;color:#fff;background:var(--god)}
.note{background:var(--surface);border-left:3px solid var(--accent);padding:8px 12px;border-radius:4px;color:var(--ink2);font-size:13px}
details{margin:8px 0} summary{cursor:pointer;color:var(--accent)} code{font-size:12px}
"""


def build(cells_in: list[tuple[str, Path]], out: Path) -> dict[str, Any]:
    cells, skipped = [], []
    for lab, p in cells_in:
        c = load_cell(p)
        if not c["worlds"]:
            skipped.append((lab, p, c["status"]))
            continue
        cells.append((lab, c))
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                                check=False).stdout.strip()
    except OSError:
        commit = "?"
    parts = [f"<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport "
             f"content='width=device-width, initial-scale=1'><title>Keys & God results</title><style>{CSS}</style>"
             "</head><body><main>",
             "<h1>Keys &amp; God: results dashboard</h1>",
             f"<p class=sub>Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} from run logs at commit "
             f"<code>{html.escape(commit)}</code> by <code>python -m swarm.viz.dashboard</code>. "
             f"{len(cells)} cell(s) shown, {len(skipped)} skipped (no finished God/no-God pair yet).</p>"]
    nav = ["<nav><a href='#overview'>overview</a>"] + [f"<a href='#c{k}'>{html.escape(lab)}</a>"
                                                       for k, (lab, _) in enumerate(cells)] + ["</nav>"]
    parts += nav
    parts.append("<div class=kpis>")
    for lab, c in cells:
        s = stats_row(deltas(c, "welfare", "god"))
        parts.append(f"<div class=kpi><span>{html.escape(lab)}: Δ welfare (God − no God)</span><b>{num(s['mean'])}</b>"
                     f"<span>95% t-CI {ci(s['tlo'], s['thi'])} · p={s['p']:.2f} · n={s['n']}</span></div>")
    parts.append("</div>")
    parts.append(
        "<div class=note><b>How to read.</b> Each world is played as paired branches from the same seeds: "
        "<b>with God</b>, <b>no God</b>, and in some cells a <b>re-run without God</b> (noise baseline: a fresh "
        "sample that shares no cached replies, so it differs from round 1). Δ is computed per world, then "
        "averaged. The primary interval is the Student-t 95% CI; p is an exact two-sided sign-flip test; "
        "MDE = smallest mean Δ detectable with 80% power at this n. Divergence counts agents whose actions "
        "(kind, target, info id) differ from the no-God branch; it is measured against zero, so compare the God "
        "row with the re-run row, not with 0. Numbers per agent are per agent over the whole game.</div>")
    parts.append("<h2 id=overview>Overview</h2>")
    parts.append(overview_table(cells))
    parts.append(f"<div class=fig>{chart_overview(cells)}<p class=cap>Δ welfare per world for every cell; gray "
                 "rows are the God-free re-run baselines.</p></div>")
    ct = contrast_table(cells)
    if ct:
        parts.append(f"<h3>Contrasts against {html.escape(cells[0][0])} (dose, turn mode, sweep knobs)</h3>{ct}")
    for k, (lab, c) in enumerate(cells):
        cf = c["config"]
        parts.append(f"<h2 id=c{k}>{html.escape(lab)} <span class=dim style='font-weight:400;font-size:13px'>"
                     f"{html.escape(c['path'])}</span></h2>")
        parts.append(f"<p class=sub>{cf.get('n_agents')} agents · {cf.get('keys_per_agent') or 5} keys each · "
                     f"{cf.get('max_rounds')} rounds · "
                     f"{cf.get('turn_mode')} turns · God K={cf.get('god_k')} "
                     f"({html.escape(', '.join(cf.get('schedule') or []))}) · {len(c['worlds'])} of "
                     f"{c['n_worlds_total']} worlds finished and healthy"
                     + (f" · unhealthy worlds dropped: {c['unhealthy_worlds']}" if c["unhealthy_worlds"] else "")
                     + "</p>")
        parts.append("<h3>Effects per metric (Δ = God − no God, per world)</h3>")
        parts.append(effect_table(c))
        parts.append("<div class=grid>")
        has_noise = bool(deltas(c, "welfare", "noise"))
        parts.append(f"<div class=fig>{chart_god_vs_noise(c)}<p class=cap>" + (
            "God effect next to the noise baseline, per world: if the blue dots spread no wider than the hollow "
            "ones, God is not distinguishable from chance." if has_noise else
            "God effect per world. This cell has no re-run baseline; compare the spread with the G1 re-run "
            "rows above.") + "</p></div>")
        parts.append(f"<div><div class=fig>{chart_distributions(c)}<p class=cap>Final welfare per world, by "
                     f"branch.</p></div><div class=fig style='margin-top:12px'>{chart_divergence(c)}<p class=cap>"
                     "Agents diverged from no-God, aligned on each branch's own fork round (God: first move; "
                     "re-run: first differing round). Thin = one world.</p></div></div>")
        parts.append("</div>")
        parts.append(f"<h3>Mean trajectories over rounds</h3><div class=fig>{chart_trajectories(c['path'])}"
                     "<p class=cap>Mean over worlds at the end of each round (games that ended early hold their "
                     "final values).</p></div>")
        parts.append("<h3>LLM health and cost, by branch</h3>")
        parts.append(health_table(c))
        parts.append(world_table(c))
    if skipped:
        parts.append("<h2>Skipped cells</h2><ul>" + "".join(
            f"<li>{html.escape(lab)} (<code>{html.escape(str(p))}</code>): status {html.escape(str(st))}</li>"
            for lab, p, st in skipped) + "</ul>")
    parts.append("<p class=sub style='margin-top:40px'>Metric definitions: " + "; ".join(
        f"<b>{html.escape(v[0])}</b> = {html.escape(v[1])}" for v in list(GAME_METRICS.values())
        + list(PAIR_METRICS.values())) + ".</p></main></body></html>")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(parts), encoding="utf-8")
    return {"out": str(out), "cells": [lab for lab, _ in cells], "skipped": [lab for lab, *_ in skipped]}


def discover(patterns: list[str]) -> list[tuple[str, Path]]:
    out = []
    for pat in patterns:
        for p in sorted(glob.glob(pat)):
            q = Path(p)
            if q.is_dir() and (q / "games").is_dir():
                out.append((q.name.replace("sweep_", "sweep: ", 1), q))
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("out", type=Path)
    ap.add_argument("--cell", action="append", default=[], help='"label=run_dir"; the first is the reference cell')
    ap.add_argument("--sweeps", action="append", default=[], help='glob of extra run dirs, e.g. "runs/sweep_*"')
    ap.add_argument("--per-run", action="store_true", help="also write <run_dir>/dashboard.html per cell")
    a = ap.parse_args(argv)
    cells = [(c.rsplit("=", 1)[0], Path(c.rsplit("=", 1)[1])) for c in a.cell] + discover(a.sweeps)
    info = build(cells, a.out)
    print(info)
    if a.per_run:
        for lab, p in cells:
            print(build([(lab, p)], p / "dashboard.html"))


if __name__ == "__main__":
    main()
