from __future__ import annotations

import shutil

import jinja2
import pytest

from swarm.context.base import PassthroughPolicy, WordCounter, items_from_observation
from swarm.prompts import TEMPLATES_DIR, PromptSet, load_prompt_set, prompt_hash
from swarm.schema import AgentMessageView, ChatMessage, KeyView, Observation, PinnedFacts
from tests.fixtures.fixed_state import AGENTS


def _sys_ctx(cot_mode="explicit"):
    return {"game": {"n_agents": 4, "max_rounds": 5, "actions_per_turn": 2, "grep_enabled": True},
            "cot_mode": cot_mode, "scratchpad": True}


def _view(agent: str):
    pinned = PinnedFacts(agent=agent, round=2, max_rounds=5, needs_open=[3], needs_burned=[],
                         holdings=[KeyView(info_id=1, key=1111)], can_give=[1], score=0.5, peers=AGENTS)
    obs = Observation(agent=agent, round=2, turn_index=4, pinned=pinned,
                      inbox=[AgentMessageView(msg_id="m1", channel="dm", sender="blue_owl", receiver=agent,
                                              text="hello")])
    b = PassthroughPolicy().build(agent=agent, round=2, ledger=[], current=items_from_observation(obs),
                                  memory=[], pinned=pinned, budget=14000, counter=WordCounter())
    return b.to_view()


def test_default_set_loads_and_renders_every_mode():
    ps = load_prompt_set("agent/v1")
    for mode in ("none", "explicit", "native"):
        s = ps.render("system.j2", **_sys_ctx(mode))
        assert "JSON" in s
    t = ps.render("turn.j2", view=_view("amber_fox"))
    assert "DM from blue_owl: hello" in t and "amber_fox" in t
    assert ps.render("retry.j2", error="bad json").startswith("Your last reply")


def test_system_prompt_agent_independent_and_no_god():
    ps = load_prompt_set("agent/v1")
    s = ps.render("system.j2", **_sys_ctx())
    assert all(a not in s for a in AGENTS)
    assert "god" not in s.lower() and "adversar" not in s.lower()   # agents are not told God exists


def test_hash_stable_and_sensitive(tmp_path):
    a, b = PromptSet("agent/v1"), PromptSet("agent/v1")
    assert a.hash == b.hash and len(a.hash) == 64
    root = tmp_path / "t"
    shutil.copytree(TEMPLATES_DIR, root)
    assert PromptSet("agent/v1", root=root).hash == a.hash
    p = root / "agent" / "v1" / "turn.j2"
    p.write_text(p.read_text() + " ")
    assert PromptSet("agent/v1", root=root).hash != a.hash


def test_framing_changes_hash_and_is_prepended(tmp_path):
    root = tmp_path / "t"
    shutil.copytree(TEMPLATES_DIR, root)
    plain = PromptSet("agent/v1", root=root)
    empty = PromptSet("agent/v1", framing="framing/none", root=root)
    assert empty.render("system.j2", **_sys_ctx()) == plain.render("system.j2", **_sys_ctx())
    (root / "framing" / "coop").mkdir()
    (root / "framing" / "coop" / "framing.j2").write_text("You are part of a team.")
    coop = PromptSet("agent/v1", framing="framing/coop", root=root)
    assert coop.hash != plain.hash and empty.hash != coop.hash
    assert coop.render("system.j2", **_sys_ctx()).startswith("You are part of a team.")
    assert coop.manifest()["framing"] == "framing/coop"


def test_strict_undefined():
    with pytest.raises(jinja2.UndefinedError):
        load_prompt_set("agent/v1").render("system.j2", cot_mode="none", scratchpad=True)


def test_render_deterministic_and_prompt_hash():
    ps = load_prompt_set("agent/v1")
    m1 = [ChatMessage(role="system", content=ps.render("system.j2", **_sys_ctx())),
          ChatMessage(role="user", content=ps.render("turn.j2", view=_view("amber_fox")))]
    m2 = [ChatMessage(role="system", content=ps.render("system.j2", **_sys_ctx())),
          ChatMessage(role="user", content=ps.render("turn.j2", view=_view("amber_fox")))]
    assert prompt_hash(m1) == prompt_hash(m2)
    assert prompt_hash(m1) == prompt_hash([m.model_dump() for m in m1])
    m3 = m1[:1] + [ChatMessage(role="user", content=ps.render("turn.j2", view=_view("blue_owl")))]
    assert prompt_hash(m3) != prompt_hash(m1)


def test_truth_objects_rejected(fixed_state):
    ps = load_prompt_set("agent/v1")
    with pytest.raises(TypeError, match="AgentView"):
        ps.render("turn.j2", view=fixed_state)
    with pytest.raises(TypeError, match="AgentView"):
        ps.render("turn.j2", view=_view("a"), extra=[fixed_state.messages[0]])


def test_missing_set():
    with pytest.raises(FileNotFoundError):
        PromptSet("agent/nope")
