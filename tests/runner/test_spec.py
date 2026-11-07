"""Run specs and experiment loading: paired forks share seeds (CRN); the noise replica does not."""

from __future__ import annotations

import pytest

from swarm.config import REPO_ROOT
from swarm.runner.run import load_experiment
from swarm.runner.spec import RunnerOpts, build_specs

DEMO = REPO_ROOT / "configs" / "demo.yaml"


def test_demo_config_shape() -> None:
    cfg, opts = load_experiment(DEMO)
    assert cfg.game.n_agents == 20 and cfg.game.max_rounds == 15
    assert cfg.game.turn_mode == "sequential"
    assert cfg.god.kind == "scripted" and cfg.god.budget.k == 2
    assert sorted(s.power for s in cfg.god.schedule) == ["cot_control", "message_fraud"]
    assert cfg.model_for("agent")[0] == "vllm"
    assert opts.fork.enabled and opts.engine == "real"


def test_runner_overrides_split() -> None:
    cfg, opts = load_experiment(DEMO, ["runner.engine=synth", "game.max_rounds=4"])
    assert opts.engine == "synth" and cfg.game.max_rounds == 4


def test_unknown_runner_key_rejected() -> None:
    with pytest.raises(ValueError):
        RunnerOpts.from_dict({"bogus": 1})


def test_fork_pairs_share_seeds_noise_differs() -> None:
    cfg, opts = load_experiment(DEMO, ["runner.fork.noise_replica=true", "run.n_games=2"])
    groups = build_specs(cfg, opts)
    assert len(groups) == 2
    for g in groups:
        a, b, n = g
        assert (a.branch, b.branch, n.branch) == ("god", "nogod", "noise")
        assert a.god_active and not b.god_active and not n.god_active
        assert a.game_id == b.game_id != n.game_id
        assert a.world_seed == b.world_seed == n.world_seed
        assert a.cfg.run.replica == b.cfg.run.replica != n.cfg.run.replica
    assert groups[0][0].game_id != groups[1][0].game_id


def test_fork_without_god_rejected() -> None:
    cfg, opts = load_experiment(DEMO, ["god.kind=none"])
    with pytest.raises(ValueError):
        build_specs(cfg, opts)
