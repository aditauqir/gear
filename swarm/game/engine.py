"""Game engine (WP1b): the round/turn loop. No LLM import: decisions are INJECTED.

    decide(obs: Observation, grep: GrepResult | None) -> AgentOutput   (sync or async)
        Called once per agent turn with grep=None. If the output contains a grep_log action (and grep
        is enabled), the engine runs it and calls decide AGAIN with the GrepResult; the second output
        is the final one (it may use actions_per_turn - 1 further actions; grep is once per turn).
    god_hook(state, round, next_turn) -> list[EventBody]                 (sync or async, optional)
        Called before every agent turn (sequential) / before the round's observations (simultaneous)
        with state.turn_index = next_turn - 1, so anything it delivers is stamped like the previous
        slot's real actions. The hook decides itself whether to act (start_round, wake schedule, ...).

Round r (sequential, default): order = fixed or reshuffled by make_rng(seed, game_id, "order", r);
for each position p: slot t = turn_index(r, p, N); skip agents that are delayed or sat out (the slot
is still counted); otherwise god_hook -> observe -> mark_observed -> decide -> turn event -> apply each
action -> memory.write(cot, note). Simultaneous: god_hook, observe all at slot (r-1)*N, decide all
(asyncio.gather), resolve in priority order stamped at their own slots.
End of round: round_end event + deep-copied snapshot. Game ends at max_rounds or when every agent is
done (won or no open need).
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from swarm.config import RunConfig
from swarm.memory import MemoryStore
from swarm.rng import canonical_json, make_rng, sha256_hex
from swarm.schema import (
    ActionResultData,
    AgentId,
    AgentOutcome,
    AgentOutput,
    EventBody,
    EventSink,
    GameEndData,
    GameStartData,
    GameState,
    GrepLog,
    GrepResult,
    MemorySink,
    Noop,
    Observation,
    Outcome,
    RoundEndData,
    TurnData,
    turn_index,
)

from . import rules
from .observe import grep_log, mark_observed, observe

DecideFn = Callable[[Observation, GrepResult | None], AgentOutput | Awaitable[AgentOutput]]
GodHook = Callable[[GameState, int, int], list[EventBody] | Awaitable[list[EventBody]]]


async def _maybe_await(x: Any) -> Any:
    return await x if inspect.isawaitable(x) else x


class GameEngine:
    """Runs one game. `state` is mutated in place; `snapshots` holds end-of-round deep copies."""

    def __init__(self, cfg: RunConfig, state: GameState, decide: DecideFn, *,
                 god_hook: GodHook | None = None, sink: EventSink | None = None, seed: int | None = None,
                 memory: MemoryStore | None = None) -> None:
        self.cfg, self.g = cfg, cfg.game
        self.state = state
        self.decide = decide
        self.god_hook = god_hook
        self.sink: EventSink = sink or MemorySink(game_id=state.game_id)
        self.seed = cfg.run.seed if seed is None else seed
        self.memory = memory or MemoryStore(cfg.reasoning)
        self.obs_turns: dict[AgentId, list[int]] = {a: [] for a in state.agents}   # for grep_log
        self.snapshots: list[GameState] = []
        self.end_reason: str | None = None
        self._started = False

    # ------------------------------------------------------------------ helpers
    def emit(self, bodies: list[EventBody]) -> None:
        for b in bodies:
            self.sink.emit(b)

    def _body(self, data, *, actor: str = "SYSTEM", phase="end", turn: int | None = None) -> EventBody:
        return EventBody(round=self.state.round, turn_index=turn, phase=phase, actor=actor, data=data)

    def active(self, agent: AgentId) -> bool:
        """May `agent` take a turn this round? (not delayed; not a sat-out winner)."""
        s = self.state.agents[agent]
        if self.state.round <= s.delayed_until_round:
            return False
        if self.g.winner_policy == "sit_out" and s.won_round is not None:
            return False
        return True

    def order_for_round(self, r: int) -> list[AgentId]:
        names = sorted(self.state.agents) if self.g.turn_order == "reshuffle" else list(self.state.order)
        if self.g.turn_order == "reshuffle":
            make_rng(self.seed, self.state.game_id, "order", r).shuffle(names)
        return names

    def scores(self) -> dict[AgentId, float]:
        return {a: rules.score(self.state, a) for a in sorted(self.state.agents)}

    def all_done(self) -> bool:
        return all(rules.is_done(self.state, a) for a in self.state.agents)

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> None:
        if self._started:
            return
        self._started = True
        st = self.state
        self.emit([EventBody(round=0, turn_index=None, phase="setup", actor="SYSTEM", data=GameStartData(
            config_hash=self.cfg.config_hash(), n_agents=len(st.agents), max_rounds=self.g.max_rounds,
            order=list(st.order), agents={a: s.model_copy(deep=True) for a, s in st.agents.items()},
            branch=self.cfg.run.branch, replica=self.cfg.run.replica))])
        self.snapshots.append(st.model_copy(deep=True))

    async def _god(self, r: int, next_turn: int) -> None:
        if self.god_hook is None:
            return
        self.state.turn_index = next_turn - 1
        self.emit(list(await _maybe_await(self.god_hook(self.state, r, next_turn))))

    async def _decide(self, obs: Observation) -> tuple[AgentOutput, AgentOutput | None, GrepResult | None]:
        first: AgentOutput = await _maybe_await(self.decide(obs, None))
        grep_act = next((a for a in first.actions if isinstance(a, GrepLog)), None)
        if grep_act is None:
            return first, None, None
        res = grep_log(self.state, obs.agent, self.g, grep_act.pattern, self.obs_turns[obs.agent],
                       rounds=grep_act.rounds)
        if not self.g.view_log.grep_enabled or self.g.view_log.content == "none":
            return first, None, None
        second: AgentOutput = await _maybe_await(self.decide(obs, res))
        return first, second, res

    def _observe(self, agent: AgentId, t: int) -> Observation:
        obs = observe(self.state, agent, self.g, t)
        mark_observed(self.state, agent, t)
        self.obs_turns[agent].append(t)
        return obs

    def _resolve(self, agent: AgentId, t: int, obs: Observation, first: AgentOutput,
                 second: AgentOutput | None, grep: GrepResult | None) -> None:
        st = self.state
        st.turn_index = t
        final = second or first
        limit = self.g.actions_per_turn
        planned: list = []
        if grep is not None:
            g = next(a for a in first.actions if isinstance(a, GrepLog))
            planned.append(g)
        planned += [a for a in final.actions if not isinstance(a, GrepLog) or grep is None]
        cot = final.cot if final.cot is not None else first.cot
        note = final.note if final.note is not None else first.note
        self.emit([EventBody(round=st.round, turn_index=t, phase="agents", actor=agent, data=TurnData(
            agent=agent, obs=obs, obs_hash=sha256_hex(canonical_json(obs)),
            llm_call_ids=first.llm_call_ids + (second.llm_call_ids if second else []),
            cot=cot, note=note, actions=planned, parse_ok=final.parse_ok,
            retries=first.retries + (second.retries if second else 0),
            errors=first.errors + (second.errors if second else [])))])
        used_grep = False
        for n, act in enumerate(planned):
            if n >= limit:
                self.emit([self._body(ActionResultData(agent=agent, action=act, ok=False, reason="action_limit"),
                                      actor=agent, phase="resolve", turn=t)])
                continue
            if isinstance(act, GrepLog):
                ok = grep is not None and not used_grep
                used_grep = True
                self.emit([self._body(ActionResultData(
                    agent=agent, action=act, ok=ok, reason=None if ok else "grep_unavailable",
                    n_hits=len(grep.hits) if (ok and grep) else None), actor=agent, phase="resolve", turn=t)])
                continue
            _, evs = rules.apply(st, agent, act, self.g)
            self.emit(evs)
        if self.cfg.reasoning.cot_mode != "none" and cot:
            _, ev = self.memory.write(st, agent, "cot", st.round, cot)
            self.emit([ev])
        if self.cfg.reasoning.scratchpad.enabled and note:
            _, ev = self.memory.write(st, agent, "scratchpad", st.round, note)
            self.emit([ev])

    async def run_round(self) -> None:
        """Play the next round (state.round + 1)."""
        self.start()
        st = self.state
        st.round += 1
        r, n = st.round, len(st.agents)
        st.order = self.order_for_round(r)
        if self.g.turn_mode == "sequential":
            for p, agent in enumerate(list(st.order)):
                t = turn_index(r, p, n)
                if not self.active(agent):
                    continue
                await self._god(r, t)
                st.turn_index = t
                obs = self._observe(agent, t)
                first, second, grep = await self._decide(obs)
                self._resolve(agent, t, obs, first, second, grep)
        else:
            s0 = turn_index(r, 0, n)
            await self._god(r, s0)
            st.turn_index = s0
            actors = [a for a in st.order if self.active(a)]
            obs_by = {a: self._observe(a, s0) for a in actors}
            outs = await asyncio.gather(*(self._decide(obs_by[a]) for a in actors))
            pos = {a: p for p, a in enumerate(st.order)}
            for a, (first, second, grep) in zip(actors, outs, strict=True):
                self._resolve(a, turn_index(r, pos[a], n), obs_by[a], first, second, grep)
        st.turn_index = turn_index(r + 1, 0, n) - 1
        sc = self.scores()
        self.emit([self._body(RoundEndData(state_hash=st.state_hash(), scores=sc,
                                           welfare=sum(sc.values()) / max(len(sc), 1)))])
        self.snapshots.append(st.model_copy(deep=True))

    def outcome(self) -> Outcome:
        st = self.state
        sc = self.scores()
        per = {a: AgentOutcome(score=sc[a], won_round=s.won_round, burned=list(s.burned), lost=list(s.lost))
               for a, s in sorted(st.agents.items())}
        n = max(len(per), 1)
        return Outcome(game_id=st.game_id, rounds_played=st.round, end_reason=self.end_reason or "max_rounds",
                       per_agent=per, welfare=sum(sc.values()) / n,
                       win_rate=sum(1 for o in per.values() if o.won_round is not None) / n)

    async def run(self, max_rounds: int | None = None) -> Outcome:
        """Play until max_rounds or all agents done; emits game_end and returns the Outcome."""
        self.start()
        limit = max_rounds or self.g.max_rounds
        while self.state.round < limit:
            if self.all_done():
                self.end_reason = "all_done"
                break
            await self.run_round()
        else:
            self.end_reason = "all_done" if self.all_done() else "max_rounds"
        self.state.done = True
        out = self.outcome()
        self.emit([self._body(GameEndData(outcome=out))])
        return out


def play_game(cfg: RunConfig, state: GameState, decide: DecideFn, **kw: Any) -> tuple[Outcome, GameEngine]:
    """Synchronous convenience wrapper: run a whole game, return (outcome, engine)."""
    eng = GameEngine(cfg, state, decide, **kw)
    return asyncio.run(eng.run()), eng


def noop_decide(obs: Observation, grep: GrepResult | None = None) -> AgentOutput:
    """Decision stub that does nothing."""
    return AgentOutput(actions=[Noop()])
