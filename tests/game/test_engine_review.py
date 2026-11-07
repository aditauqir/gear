"""Code-review regressions for game/engine.py (plan/CODE_REVIEW.md)."""

from __future__ import annotations

import asyncio

from swarm.game.engine import GameEngine
from swarm.llm.base import BudgetExceeded
from swarm.schema import AgentOutput, MemorySink, Noop

from .helpers import FOUR, fresh_game, run_cfg


class _Budgeted:
    """ann raises BudgetExceeded at once; the others are slow LLM calls that would keep running."""

    def __init__(self, agent: str, started: list[str], finished: list[str]) -> None:
        self.agent, self.started, self.finished = agent, started, finished

    async def act(self, obs, **_kw) -> AgentOutput:
        self.started.append(self.agent)
        if self.agent == "ann":
            raise BudgetExceeded("run", 1.0, 0.1, 1.0)
        await asyncio.sleep(0.2)
        self.finished.append(self.agent)
        return AgentOutput(actions=[Noop()])


def test_simultaneous_failure_cancels_sibling_turns():
    """Review: asyncio.gather does not cancel the other act() calls when one raises, so after
    BudgetExceeded they kept running (and spending) after game_end. They must be cancelled."""
    cfg = run_cfg(game={"turn_mode": "simultaneous", "max_rounds": 3})
    started: list[str] = []
    finished: list[str] = []
    agents = {a: _Budgeted(a, started, finished) for a in FOUR}

    async def main() -> tuple[str, list[asyncio.Task]]:
        eng = GameEngine(cfg, fresh_game(FOUR), agents, sink=MemorySink())
        out = await eng.run()
        await asyncio.sleep(0.3)                 # give leaked tasks time to finish
        others = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        return out.end_reason, others

    end_reason, leftover = asyncio.run(main())
    assert end_reason == "budget_exceeded"
    assert sorted(started) == sorted(FOUR)
    assert finished == [] and leftover == []


def test_empty_ledgers_dict_is_used_not_replaced():
    """Review: `ledgers or {...}` dropped a caller's (still empty) dict, so it never filled up."""
    cfg = run_cfg(game={"max_rounds": 1})
    ledgers: dict = {a: [] for a in FOUR}
    passed: dict = {}
    eng = GameEngine(cfg, fresh_game(FOUR), lambda obs, g: AgentOutput(actions=[Noop()]), ledgers=passed)
    assert eng.ledgers is passed
    eng2 = GameEngine(cfg, fresh_game(FOUR), lambda obs, g: AgentOutput(actions=[Noop()]), ledgers=ledgers)
    asyncio.run(eng2.run())
    assert all(ledgers[a] for a in FOUR)
