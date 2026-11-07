from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from swarm.config import REPO_ROOT, RunConfig, expand_sweep, from_dict, load, parse_override


def test_defaults_validate_and_match_lead_decisions():
    c = RunConfig()
    assert c.game.turn_mode == "sequential" and c.game.defect_gain == "mint"
    assert c.game.wrong_defect_penalty == "lose_need" and c.game.winner_policy == "continue"
    v = c.game.view_log
    assert (v.content, v.actor_identity, v.reveal_provenance) == ("actions_only", "shown", False)
    assert v.defect_visibility == "victim_then_delayed" and v.defect_delay_rounds == 3 and v.grep_enabled
    assert c.game.window_turns == c.game.n_agents
    assert c.reasoning.cot_replay_window == 0 and c.reasoning.cot_mode in ("none", "native", "explicit")
    assert c.god.powers.cot_control.targets == ["scratchpad"] and c.god.powers.cot_control.mode == "replace"
    assert c.god.tool_call_safety_ceiling == 50
    assert c.context.policy == "full_truncate" and c.context.budget_tokens == 14000
    assert c.roles.agent.max_tokens == 700
    assert c.llm.openrouter.enabled is False and c.llm.openrouter.global_cap_usd == 6.0
    assert c.llm.openrouter.model == "qwen/qwen3.6-35b-a3b"
    assert c.model_for("agent") == ("vllm", "Qwen/Qwen3-8B")


def test_base_yaml_equals_code_defaults():
    assert load(REPO_ROOT / "configs" / "base.yaml") == RunConfig()


def test_extra_forbid_rejects_typo():
    with pytest.raises(ValidationError):
        from_dict({"game": {"n_agent": 10}})


def test_overrides_parse_types():
    c = from_dict({}, ["game.n_agents=10", "game.view_log.reveal_provenance=true",
                       "run.name=foo"])
    assert c.game.n_agents == 10 and c.game.view_log.reveal_provenance is True
    assert c.run.name == "foo"
    assert parse_override("a.b=3") == (["a", "b"], 3)
    assert parse_override("x=[1,2]") == (["x"], [1, 2])
    with pytest.raises(ValueError):
        parse_override("novalue")


def test_extends_deep_merge_and_list_replace(tmp_path: Path):
    base = {"game": {"n_agents": 8, "max_rounds": 9},
            "god": {"powers": {"cot_control": {"targets": ["scratchpad"]}}}}
    (tmp_path / "base.yaml").write_text(yaml.safe_dump(base))
    (tmp_path / "exp.yaml").write_text(yaml.safe_dump({"extends": "base.yaml", "game": {"n_agents": 12}}))
    c = load(tmp_path / "exp.yaml", ["game.max_rounds=11"])
    assert (c.game.n_agents, c.game.max_rounds) == (12, 11)
    (tmp_path / "exp2.yaml").write_text(yaml.safe_dump({"extends": "exp.yaml"}))
    with pytest.raises(ValueError, match="one level"):
        load(tmp_path / "exp2.yaml")


@pytest.mark.parametrize("over, msg", [
    (["god.powers.cot_control.targets=[cot]"], "cot_replay_window"),
    (["god.powers.cot_control.targets=[cot]", "reasoning.cot_replay_window=2", "reasoning.cot_mode=none"],
     "cot_mode"),
    (["god.powers.cot_control.targets=[summary]"], "summarizing"),
    (["reasoning.scratchpad.enabled=false"], "scratchpad"),
    (["context.budget_tokens=16000"], "max_model_len"),
    (["roles.agent.backend=openrouter"], "openrouter.enabled"),
    (["context.policy=rolling_summary"], "stub"),
    (["context.policy=hybrid"], "stub"),
    (["game.immediate_reply=true"], "not implemented"),
    (["game.observe_mode=tools"], ""),
    (["game.actions_per_turn=3"], ""),
    (["game.turn_mode=parallel"], ""),
])
def test_cross_field_errors(over, msg):
    with pytest.raises(ValidationError, match=msg or None):
        from_dict({}, over)


def test_valid_alternatives():
    c = from_dict({}, ["god.powers.cot_control.targets=[cot, scratchpad]", "reasoning.cot_replay_window=2",
                       "context.policy=window", "game.turn_mode=simultaneous", "game.defect_gain=steal",
                       "game.wrong_defect_penalty=delay", "game.winner_policy=sit_out",
                       "llm.openrouter.enabled=true", "roles.god.backend=openrouter",
                       "game.view_log.window_turns=5"])
    assert c.model_for("god") == ("openrouter", "qwen/qwen3.6-35b-a3b")
    assert c.game.window_turns == 5


def test_sweep_expansion_and_hash():
    c = from_dict({"sweep": {"god.budget.k": [0, 1, 3], "run.seed": [0, 1]}})
    cells = expand_sweep(c)
    assert len(cells) == 6
    assert {(p["god.budget.k"], p["run.seed"]) for p, _ in cells} == {(k, s) for k in (0, 1, 3) for s in (0, 1)}
    assert all(cc.sweep == {} for _, cc in cells)
    assert len({cc.config_hash() for _, cc in cells}) == 6
    assert RunConfig().config_hash() == RunConfig().config_hash()
    assert from_dict({}, ["run.seed=1"]).config_hash() != RunConfig().config_hash()


def test_config_hash_ignores_global_cap():
    """The $2 -> $6 cap raise must not re-key games: hashes pinned from commit 1993b5c (cap $2)."""
    from swarm.runner.run import load_experiment

    pinned = {"base": "b442ad7af4a87da8bb2ff289c1e794cd7b98f44742c8a7066966921cfad35ee1",
              "demo": "e657c252cf92bdb031139dfb827beda2878b0ddd04d8451e06fdedcd6f8d2d38",
              "demo_openrouter": "29d5b81fed03ede6bbcc85b02f2000dc7fb2020330fc2ee101d0bb523636dbe7"}
    assert RunConfig().config_hash() == pinned["base"]
    for name, h in pinned.items():
        for cap in (None, 2.0, 6.0, 100.0):
            ov = [] if cap is None else [f"llm.openrouter.global_cap_usd={cap}"]
            assert load_experiment(REPO_ROOT / "configs" / f"{name}.yaml", ov)[0].config_hash() == h, (name, cap)
    # budget_usd is still part of the hash (past runs overrode it)
    assert from_dict({}, ["llm.budget_usd=0.75"]).config_hash() != RunConfig().config_hash()
