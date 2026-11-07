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
