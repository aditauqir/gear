"""Code-review regressions for runner/wiring.py (plan/CODE_REVIEW.md)."""

from __future__ import annotations

import pytest

from swarm.config import from_dict
from swarm.runner.wiring import check_schedule


def _cfg(turn_mode: str, after_turns: int, n_agents: int = 4):
    return from_dict({"game": {"n_agents": n_agents, "turn_mode": turn_mode},
                      "god": {"kind": "scripted", "start_round": 1,
                              "schedule": [{"round": 1, "after_turns": after_turns,
                                            "power": "message_fraud"}]}})


def test_schedule_after_turns_rejected_in_simultaneous_mode() -> None:
    """Simultaneous mode consults God only at slot 0, so after_turns > 0 used to be a silent no-op."""
    check_schedule(_cfg("simultaneous", 0))
    with pytest.raises(ValueError, match="simultaneous"):
        check_schedule(_cfg("simultaneous", 2))


def test_schedule_after_turns_beyond_round_rejected_in_sequential_mode() -> None:
    check_schedule(_cfg("sequential", 3))
    with pytest.raises(ValueError, match="never fires"):
        check_schedule(_cfg("sequential", 4))


def test_schedule_check_ignores_non_scripted_god() -> None:
    cfg = from_dict({"game": {"turn_mode": "simultaneous"}, "god": {"kind": "none",
                     "schedule": [{"round": 1, "after_turns": 5, "power": "message_fraud"}]}})
    check_schedule(cfg)


def test_ledger_sink_numbers_own_actions_per_turn() -> None:
    """Review bug 1: LedgerSink gave every own action item_id '<agent>:<round>:own_action:0', so the
    context policy (items keyed by id) showed a 2-action turn's second action twice and lost the first."""
    from swarm.agents.llm_agent import LLMAgent
    from swarm.context.base import WordCounter
    from swarm.runner.wiring import LedgerSink
    from swarm.schema import ActionResultData, EventBody, GiveKey, MemorySink, PinnedFacts, PostBoard

    sink = LedgerSink(MemorySink(), WordCounter())
    acts = [PostBoard(text="looking for info 6"), GiveKey(to="bob", info_id=1)]
    for rnd in (1, 2):
        for a in acts:
            sink.emit(EventBody(round=rnd, turn_index=0, phase="resolve", actor="ann",
                                data=ActionResultData(agent="ann", action=a, ok=True)))
    ids = [it.item_id for it in sink.ledgers["ann"]]
    assert len(ids) == len(set(ids)) == 4
    cfg = from_dict({"roles": {r: {"backend": "fake"} for r in ("agent", "god", "judge", "summarizer")},
                     "context": {"tokenizer": "words"}, "god": {"kind": "none"}})
    agent = LLMAgent("ann", None, cfg)   # build_messages only; no LLM call
    pinned = PinnedFacts(agent="ann", round=3, max_rounds=5, needs_open=[], needs_burned=[], holdings=[],
                         can_give=[], score=0.0, peers=["bob"])
    bundle = agent.policy.build(agent="ann", round=3, ledger=sink.ledgers["ann"], current=[], memory=[],
                                pinned=pinned, budget=cfg.context.budget_tokens, counter=WordCounter())
    user = agent.build_messages(bundle)[1].content
    assert user.count("You posted on the board: looking for info 6") == 2      # once per round
    assert user.count("You gave bob your key for info 1") == 2
