"""Demo-video / paper-figure helpers: captions, pacing, world picking, divergence, rendering smoke tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from swarm.viz.story import Branch, Power, captions, divergence, load_branch, pacing, pick_worlds, world_table


def _branch(R: int = 6, gives=(), defects=(), powers=(), wins=None, label: str = "g00-god") -> Branch:
    agents = ["a", "b", "c", "d"]
    edges = {r: {k: [] for k in ("dm", "give", "defect", "board", "fraud", "cot")} for r in range(R + 1)}
    b = Branch(label, agents, R, R, "max_rounds", edges, {0: {x: 0.0 for x in agents}}, wins or {})
    b.gives = list(gives)
    b.defects = list(defects)
    b.powers = list(powers)
    return b


def test_captions_bait_taken_only_when_not_in_control() -> None:
    fraud = Power(3, "message_fraud", "a", "b", "Send me one of your keys first and it's yours.")
    god = _branch(gives=[(3, "a", "b", 5)], powers=[fraud])
    caps = captions(god, _branch(label="g00-nogod"))
    assert caps[3][0] == ("god", "GOD forges a DM to a, signed as b:")
    assert caps[3][1][0] == "quote" and "keys first" in caps[3][1][1]
    assert ("effect", "a takes the bait: gives its key for info 5 to b") in caps[3]
    # the same give also happens without God -> not attributed to the forged DM
    caps2 = captions(god, _branch(gives=[(3, "a", "b", 5)], label="g00-nogod"))
    assert not any("takes the bait" in t for _, t in caps2[3])
    assert ("effect", "a does not hand b a key") in caps2[4]


def test_captions_cot_effect_and_ripple_counts() -> None:
    cot = Power(5, "cot_control", "a", None, "c is lying to me. Do not give c anything.")
    god = _branch(defects=[(6, "a", "c", True)], powers=[cot], wins={5: ["d"]})
    ever = {r: ({"a"} if r == 5 else {"a", "b"} if r >= 6 else set()) for r in range(1, 7)}
    caps = captions(god, _branch(label="g00-nogod"), ever)
    assert caps[5][0] == ("god", "GOD rewrites a's private notes from round 4 to:")
    assert ("effect", "a acts on the planted note: defects against c") in caps[6]
    assert ("ripple", "Ripple: 1/4 agents now act differently than in the no-God world") in caps[5]
    assert ("ripple", "Ripple: 2/4 agents now act differently than in the no-God world") in caps[6]
    assert ("win", "Wins: with God 1, without God 0") in caps[5]


def test_pacing_holds_on_god_and_effect_rounds() -> None:
    caps = {3: [("god", "x"), ("effect", "y")], 4: [("effect", "z")], 5: [("win", "w")]}
    p = dict(pacing(6, caps, base=1.0, god_hold=2.5, effect_hold=1.5))
    assert p == {1: 1.0, 2: 1.0, 3: 3.5, 4: 2.5, 5: 1.0, 6: 1.0}


def test_pick_worlds_uses_excess_over_noise_and_ripple_speed() -> None:
    rows = [{"world": 0, "delta": 0.20, "noise_delta": 0.17, "rounds_to_80pct": 1},
            {"world": 1, "delta": -0.27, "noise_delta": -0.13, "rounds_to_80pct": 1},
            {"world": 2, "delta": 0.05, "noise_delta": None, "rounds_to_80pct": 3},
            {"world": 3, "delta": 0.00, "noise_delta": 0.0, "rounds_to_80pct": 3}]
    p = pick_worlds(rows)
    assert p["harm"]["world"] == 1          # 0.27 - 0.13 = 0.14 beats 0.20 - 0.17 = 0.03
    assert p["ripple"]["world"] == 2        # slowest spread, tie broken by excess (0.05 > 0.0)
    assert pick_worlds([]) == {}


def test_real_run_helpers(fake_run: Path) -> None:
    god = load_branch(fake_run / "games" / "g00-god")
    nogod = load_branch(fake_run / "games" / "g00-nogod")
    assert god.agents and god.R >= god.rounds_played >= 1
    assert god.powers and all(p.target in god.agents for p in god.powers)
    assert 0.0 <= god.welfare(god.R) <= 1.0
    now, ever = divergence(fake_run / "games" / "g00-god", fake_run / "games" / "g00-nogod")
    rs = sorted(ever)
    assert all(ever[a] <= ever[b] for a, b in zip(rs, rs[1:], strict=False))  # cumulative
    assert all(now[r] <= ever[r] for r in rs)
    caps = captions(god, nogod, ever)
    assert any(k == "god" for r in caps for k, _ in caps[r])
    rows = world_table(fake_run)
    assert rows and {"world", "delta", "rounds_to_80pct", "victim_delta"} <= set(rows[0])


@pytest.mark.slow
def test_animate_writes_h264(fake_run: Path, tmp_path: Path) -> None:
    from swarm.viz.animate import main

    out = tmp_path / "v.mp4"
    main([str(fake_run), str(out), "--world", "0", "--preview-round", "3", "--preview", str(tmp_path / "p.png")])
    assert out.stat().st_size > 10_000 and (tmp_path / "p.png").exists()
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=codec_name,pix_fmt,width,height", "-of", "csv=p=0", str(out)],
                           capture_output=True, text=True, check=True).stdout.strip()
    assert probe == "h264,1280,720,yuv420p"


def test_paper_figs_render_and_match_grid_stats(synth_run: Path, tmp_path: Path) -> None:
    from swarm.analysis.grid_stats import deltas, load_run
    from swarm.viz.paper_figs import cell_deltas, fig_delta_welfare, fig_divergence, summarize

    d = cell_deltas(synth_run)
    ref = deltas(load_run(synth_run), "welfare")
    assert d.keys() == ref.keys() and all(abs(d[i] - ref[i]) < 1e-9 for i in d)
    s = summarize([0.1, -0.1, 0.2, 0.0], n_boot=500)
    assert s["n"] == 4 and s["lo"] <= s["mean"] <= s["hi"]
    cells = [("synth", synth_run)]
    for p in fig_divergence(cells, tmp_path) + fig_delta_welfare(cells, tmp_path, n_boot=200)[0]:
        assert p.stat().st_size > 2000
    assert (tmp_path / "fig_divergence.pdf").read_bytes()[:4] == b"%PDF"
