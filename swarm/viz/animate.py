"""Round-by-round interaction-network MP4 (God vs no-God), styled like figures.network_png.

usage: python -m swarm.viz.animate RUN_DIR OUT.mp4 [--god g00-god --nogod g00-nogod --preview-round 15 --preview PNG]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.lines import Line2D

from swarm.viz.style import C, INK, INK2, SURFACE

W, H, DPI = 1280, 720, 100


def load(path):
    ev = [json.loads(l) for l in open(path)]
    start = next(e for e in ev if e["type"] == "game_start")["data"]
    agents = list(start["order"])
    R = start["max_rounds"]
    g = {r: dict(dm=[], give=[], defect=[], fraud=[], cot=[], win=[], board=[]) for r in range(R + 1)}
    scores = {0: {a: 0.0 for a in agents}}
    for e in ev:
        r, t, d = e["round"], e["type"], e["data"]
        if t == "message":
            m = d["message"]
            if m["channel"] == "dm" and m["receiver"] and not m["forged"]:
                g[r]["dm"].append((m["sender_shown"], m["receiver"]))
            elif m["channel"] == "board":
                pass
        elif t == "action_result" and d["action"]["kind"] == "post_board" and d.get("ok"):
            g[r]["board"].append((e["actor"], "BOARD"))
        elif t == "key_transfer" and d["cause"] == "give" and d["from_agent"]:
            g[r]["give"].append((d["from_agent"], d["to_agent"]))
        elif t == "burn":
            g[r]["defect"].append((d["actor"], d["target"], bool(d["correct"])))
        elif t == "god_power" and d["ok"]:
            a = d["action"]
            if d["power"] == "message_fraud":
                g[r]["fraud"].append(a["receiver"])
            else:
                g[r]["cot"].append(a["agent"])
        elif t == "win":
            g[r]["win"].append(d["agent"])
        elif t == "round_end":
            scores[r] = d["scores"]
    ge = next((e for e in ev if e["type"] == "game_end"), None)
    g["_end"] = (ge["data"]["outcome"]["rounds_played"], ge["data"]["outcome"]["end_reason"]) if ge else (R, "")
    return agents, R, g, scores


def draw_panel(ax, title, agents, R, g, scores, pos, r):
    ax.clear(); ax.axis("off"); ax.set_xlim(-1.75, 1.75); ax.set_ylim(-1.45, 1.55)
    G = nx.DiGraph(); G.add_nodes_from(agents); G.add_node("GOD"); G.add_node("BOARD")

    def edges(kind, rr, f=lambda x: x):
        c = Counter()
        for x in g[rr][kind]:
            c[(x[0], x[1])] += 1
        return c

    def draw(c, color, style, base, alpha):
        if c:
            nx.draw_networkx_edges(G, pos, edgelist=list(c), ax=ax, edge_color=color, style=style,
                                   width=[base + 0.4 * min(n, 4) for n in c.values()], alpha=alpha,
                                   arrows=True, arrowsize=9, connectionstyle="arc3,rad=0.08", node_size=300)

    for rr in range(1, r + 1):
        cur = rr == r
        a_old, wmul = (1.0, 2.2) if cur else (0.0, 1.0)
        for kind, col in (("dm", C["dm"]), ("give", C["give"])):
            draw(edges(kind, rr), col, "solid", (1.6 if cur else 0.4), 0.9 if cur else 0.14)
        draw(edges("board", rr), C["board"], "solid", 1.6 if cur else 0.4, 0.9 if cur else 0.14)
        d = Counter((a, b) for a, b, _ in g[rr]["defect"])
        draw(d, C["defect"], "solid", 1.8 if cur else 0.5, 0.95 if cur else 0.2)
        for kind, col in (("fraud", C["fraud"]), ("cot", C["cot"])):
            c = Counter(("GOD", t) for t in g[rr][kind])
            draw(c, col, "dashed", 2.5 if cur else 1.2, 1.0 if cur else 0.45)
    won = {a for rr in range(r + 1) for a in g[rr]["win"]}
    burned = {t for rr in range(r + 1) for _, t, ok in g[rr]["defect"] if ok}
    sc = scores.get(r) or scores[max(k for k in scores if k <= r)]
    colors = [C["win"] if a in won else C["defect"] if a in burned else C["a"] for a in agents]
    sizes = [160 + 520 * sc.get(a, 0.0) for a in agents]
    nx.draw_networkx_nodes(G, pos, nodelist=agents, node_color=colors, node_size=sizes, ax=ax,
                           edgecolors=SURFACE, linewidths=1.5)
    for kind, col in (("fraud", C["fraud"]), ("cot", C["cot"])):
        t = g[r][kind]
        if t:
            nx.draw_networkx_nodes(G, pos, nodelist=list(set(t)), node_color="none", node_size=900, ax=ax,
                                   edgecolors=col, linewidths=2.4)
    nx.draw_networkx_nodes(G, pos, nodelist=["BOARD"], node_color=C["board"], node_shape="s", node_size=900, ax=ax)
    nx.draw_networkx_labels(G, pos, labels={"BOARD": "BOARD"}, font_color=SURFACE, font_size=7, ax=ax)
    anyg = any(g[rr]["fraud"] or g[rr]["cot"] for rr in range(R + 1))
    if anyg:
        nx.draw_networkx_nodes(G, pos, nodelist=["GOD"], node_color=INK2, node_shape="s", node_size=700, ax=ax)
        nx.draw_networkx_labels(G, pos, labels={"GOD": "GOD"}, font_color=SURFACE, font_size=8, ax=ax)
    nx.draw_networkx_labels(G, {a: pos[a] + np.array([0, -0.11]) for a in agents},
                            labels={a: a for a in agents}, font_size=6.5, font_color=INK2, ax=ax)
    flags = []
    if g[r]["fraud"]:
        flags.append(("God: forged DM", C["fraud"]))
    if g[r]["cot"]:
        flags.append(("God: memory overwrite", C["cot"]))
    for i, (txt, col) in enumerate(flags):
        ax.text(-1.7, 1.5 - 0.14 * i, txt, color="white", fontsize=9, fontweight="bold", va="top",
                bbox=dict(boxstyle="round,pad=0.3", fc=col, ec="none"))
    tot = lambda k: sum(len(g[rr][k]) for rr in range(1, r + 1))
    ng = tot("give"); nd = tot("defect"); nb = sum(len(g[rr]["board"]) for rr in range(1, r + 1)); nw = len(won)
    er, why = g["_end"]
    if r > er and er < R:
        title += f"  (ended r{er}" + (" (all won))" if why == "all_done" else ")")
    ax.set_title(title, fontsize=12, fontweight="bold", color=INK, loc="center")
    ax.text(0, -1.42, f"gives {ng}   |   defects {nd}   |   board posts {nb}   |   wins {nw}",
            ha="center", va="bottom", fontsize=10.5, color=INK)


def render(fig, axes, data, pos, r, R, labels):
    fig.suptitle(f"Round {r}/{R}", fontsize=18, fontweight="bold", color=INK, y=0.975)
    for ax, (agents, _, g, scores), lab in zip(axes, data, labels):
        draw_panel(ax, lab, agents, R, g, scores, pos, r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir"); ap.add_argument("out")
    ap.add_argument("--god", default="g00-god"); ap.add_argument("--nogod", default="g00-nogod")
    ap.add_argument("--preview-round", type=int); ap.add_argument("--preview")
    ap.add_argument("--hold", type=int, default=3)
    a = ap.parse_args()
    run = Path(a.run_dir)
    data = [load(run / "games" / n / "events.jsonl") for n in (a.god, a.nogod)]
    agents, R = data[0][0], data[0][1]
    U = nx.Graph(); U.add_nodes_from(agents)
    for _, _, g, _ in data:
        for rr in [k for k in g if k != '_end']:
            for k in ("dm", "give"):
                for x, y in g[rr][k]:
                    w = U.get_edge_data(x, y, {"weight": 0})["weight"]; U.add_edge(x, y, weight=w + 1)
    pos = nx.spring_layout(U, seed=0, k=1.2 / len(agents) ** 0.5)
    p = np.array(list(pos.values())); p = (p - p.mean(0)) / np.abs(p - p.mean(0)).max() * 1.05
    pos = dict(zip(pos, p)); pos["GOD"] = np.array([-1.5, 1.2]); pos["BOARD"] = np.array([1.5, 1.2])
    labels = ["With God", "No God"]
    fig, axes = plt.subplots(1, 2, figsize=(W / DPI, H / DPI), dpi=DPI)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.9, bottom=0.1, wspace=0.02)
    handles = [Line2D([], [], color=C["dm"], label="DMs"), Line2D([], [], color=C["give"], label="gives"),
               Line2D([], [], color=C["defect"], label="defects"),
               Line2D([], [], color=C["board"], label="board posts"),
               Line2D([], [], color=C["fraud"], ls="--", label="God: forged DM"),
               Line2D([], [], color=C["cot"], ls="--", label="God: memory overwrite"),
               Line2D([], [], marker="o", ls="", color=C["a"], label="active"),
               Line2D([], [], marker="o", ls="", color=C["win"], label="won"),
               Line2D([], [], marker="o", ls="", color=C["defect"], label="had a need burned")]
    fig.legend(handles=handles, loc="lower center", ncol=9, fontsize=8, frameon=False)
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        for r in range(1, R + 1):
            render(fig, axes, data, pos, r, R, labels)
            fig.savefig(f"{td}/f{r:03d}.png", dpi=DPI)
            if a.preview and r == a.preview_round:
                fig.savefig(a.preview, dpi=DPI)
        for h in range(a.hold):  # extra copies of last frame; 1 fps input
            Path(f"{td}/f{R + 1 + h:03d}.png").write_bytes(Path(f"{td}/f{R:03d}.png").read_bytes())
        subprocess.run(["/usr/bin/ffmpeg", "-y", "-loglevel", "error", "-framerate", "1", "-i", f"{td}/f%03d.png",
                        "-vf", "fps=10,scale=1280:720,format=yuv420p", "-c:v", "libx264", "-crf", "23",
                        "-movflags", "+faststart", str(out)], check=True)


if __name__ == "__main__":
    main()
