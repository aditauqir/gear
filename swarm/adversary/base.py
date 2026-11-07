"""God interface and the per-game runner (WP4).

    runner = GodRunner(god, cfg.god, memory, max_message_chars=cfg.game.max_message_chars)
    runner.init_game(state)                      # once, after generate_world (sets the budget)
    ... before each agent slot (sequential) or at round start (simultaneous):
    if runner.should_wake(state):
        res = await runner.wake(state)           # mutates state (inbox / memory / budget)
        for body in res.events: sink.emit(body)

`state.turn_index` must already be the slot about to be played: God acts *between* turns, and
forged DMs are stamped with that slot (see powers.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from swarm.adversary.god_tools import GodView
from swarm.adversary.powers import PowerResult, apply_power, init_budget, is_power, refresh_budget
from swarm.config import GodCfg
from swarm.memory import MemoryStore
from swarm.schema import EventBody, GameState, GodAction


def turns_into_round(state: GameState) -> int:
    """Agent slots already played in the current round (schema.turn_index contract)."""
    return state.turn_index - (state.round - 1) * len(state.order)


@runtime_checkable
class God(Protocol):
    name: str

    def wakes_at(self, state: GameState) -> bool:
        """Should God wake before the slot `state.turn_index`? (start_round is checked by the runner.)"""
        ...

    async def step(self, state: GameState, view: GodView) -> list[GodAction]:
        """Observe through `view` (free) and return the GodActions to apply (tools and/or powers).
        Must not mutate `state`; the runner applies powers via adversary.powers."""
        ...


@dataclass
class WakeResult:
    actions: list[GodAction] = field(default_factory=list)
    results: list[PowerResult] = field(default_factory=list)
    events: list[EventBody] = field(default_factory=list)
    ceiling_hit: bool = False


class GodRunner:
    """Owns budget refresh, the tool ceiling and power application for one game."""

    def __init__(self, god: God, cfg: GodCfg, memory: MemoryStore, *, max_message_chars: int = 500) -> None:
        self.god, self.cfg, self.memory = god, cfg, memory
        self.max_message_chars = max_message_chars
        self._budget_round: int | None = None

    def init_game(self, state: GameState) -> None:
        init_budget(state, self.cfg)
        self._budget_round = None

    def should_wake(self, state: GameState) -> bool:
        if self.cfg.kind == "none" or state.round < self.cfg.start_round:
            return False
        return self.god.wakes_at(state)

    async def wake(self, state: GameState) -> WakeResult:
        self._budget_round = refresh_budget(state, self.cfg, self._budget_round)
        view = GodView(state, ceiling=self.cfg.tool_call_safety_ceiling)
        actions = await self.god.step(state, view)
        out = WakeResult(actions=list(actions))
        for a in actions:
            if is_power(a):
                continue
            view.run(a)                       # tool actions returned by step (LLM God style)
        out.events.extend(view.events)        # tool events happened before the powers
        for a in actions:
            if not is_power(a):
                continue
            res = apply_power(state, a, self.cfg, self.memory, max_message_chars=self.max_message_chars)
            out.results.append(res)
            out.events.extend(res.events)
        out.ceiling_hit = view.exhausted
        return out
