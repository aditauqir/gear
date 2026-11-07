"""Game engine (WP1b): the round/turn loop. No LLM client import: players and God are INJECTED.

Inputs:
    agents: Mapping[AgentId, TurnAgent]  (e.g. swarm.agents.llm_agent.LLMAgent), or one DecideFn
        TurnAgent.act(obs, *, ledger, memory, game_id, grep) -> AgentOutput   (async or sync)
            `grep` is a callback GrepLog -> GrepResult (None when grep is disabled). grep_log is FREE:
            it does not use an action slot; only the first grep of a turn is run.
        DecideFn(obs, grep_result | None) -> AgentOutput  (tests / scripted stubs; adapted by
            DecideAgent: called again with the GrepResult when its first output has a grep_log).
    god: GodLike | None  (swarm.adversary.base.GodRunner): init_game(state), should_wake(state),
        await wake(state) -> object with `.events`. Called with state.turn_index = the slot about to
        be played, so anything God delivers is stamped with the wake slot.
    god_hook(state, round, next_turn) -> list[EventBody]   (legacy form of god; sync or async)
        FROZEN convention (runner/wiring.py's _SlotGod depends on it): called before every slot
        (sequential; skipped slots too) / once at the round's first slot (simultaneous) with
        next_turn = the slot about to be played and state.turn_index = next_turn - 1 on entry.
        Records the hook creates without resetting turn_index are stamped next_turn - 1, which makes
        them visible at next_turn. The engine sets state.turn_index = next_turn after the hook.
Outputs: events through `sink`, end-of-round snapshots (`snapshots`, `on_snapshot`), per-agent
ledgers (`ledgers`), and the Outcome from `run()`.

Round r, sequential (default): order = fixed, or reshuffled by make_rng(seed, game_id, "order", r).
For each position p, slot t = turn_index(r, p, N): God (before EVERY slot, skipped ones too) ->
skip if the agent is delayed / a sat-out winner (the slot still counts) -> observe at t ->
mark_observed -> act -> turn event (+ context_built) -> apply each action stamped t -> memory.write
(cot, note) -> ledger += observation items + own-action items.
Simultaneous: God once at s0 = turn_index(r, 0, N); every active agent observes at s0; all act
concurrently (asyncio.gather, bounded by the LLM client's semaphore); actions resolve in
turn-priority order (st.order: fixed or reshuffled per round), each stamped at its own slot; a
give_key / defect that fails at resolution (e.g. the key was already taken) also sends the actor a
"system" notice.
game.board.post_costs_turn (default off): a post_board uses the whole action budget of its turn. The
first post_board of a turn is applied; every other action of that turn (before or after it; grep_log
and noop excepted) fails with reason "board_post_uses_whole_turn" without using a slot, and the agent
gets one "system" notice (next observation) saying so.
send_message still costs one slot. Same in both turn modes (it is decided per agent turn in _resolve).
End of round: round_end event + deep-copied snapshot. The game ends at max_rounds, when every agent
is done (won or no open need), or on BudgetExceeded (end_reason="budget_exceeded").
Imports: config, memory, rng, schema, context.base/tokens, llm.base (BudgetExceeded only), game.*.
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any, Protocol

from swarm.config import RunConfig
from swarm.context.base import TokenCounter, items_from_observation, own_action_items
from swarm.context.tokens import make_counter
from swarm.llm.base import BudgetExceeded
from swarm.memory import MemoryStore
from swarm.rng import canonical_json, make_rng, sha256_hex
from swarm.schema import (
    Action,
    ActionResultData,
    AgentId,
    AgentOutcome,
    AgentOutput,
    ContextBuiltData,
    DefectAction,
    EventBody,
    EventSink,
    GameEndData,
    GameStartData,
    GameState,
    GiveKey,
    GrepLog,
    GrepResult,
    HistoryItem,
    MemorySink,
    MemoryView,
    Noop,
    Observation,
    Outcome,
    PostBoard,
    RoundEndData,
    TurnData,
    turn_index,
)

from . import rules
from .observe import grep_log, mark_observed, observe

DecideFn = Callable[[Observation, GrepResult | None], AgentOutput | Awaitable[AgentOutput]]
GodHook = Callable[[GameState, int, int], list[EventBody] | Awaitable[list[EventBody]]]
GrepFn = Callable[[GrepLog], GrepResult]
Result = tuple[bool, str | None]


class TurnAgent(Protocol):
    """A player: LLMAgent or any object with this act() signature."""

    def act(self, obs: Observation, *, ledger: Sequence[HistoryItem], memory: Sequence[MemoryView],
            game_id: str, grep: GrepFn | None) -> Awaitable[AgentOutput] | AgentOutput:
        """Play one turn from the observation."""
        ...


class GodLike(Protocol):
    """GodRunner's surface used by the engine (init_game is optional)."""

    def should_wake(self, state: GameState) -> bool:
        """Wake before slot state.turn_index?"""
        ...

    def wake(self, state: GameState) -> Awaitable[Any]:
        """Act on state; the result has `.events: list[EventBody]`."""
        ...


async def _maybe_await(x: Any) -> Any:
    return await x if inspect.isawaitable(x) else x


class DecideAgent:
    """Adapts a two-call DecideFn (obs, grep_result|None) to the TurnAgent protocol (tests, stubs).
    Mirrors LLMAgent: final actions = [grep_log, *follow-up actions] when a grep ran."""

    def __init__(self, decide: DecideFn) -> None:
        self.decide = decide

    async def act(self, obs: Observation, *, ledger: Sequence[HistoryItem] = (),
                  memory: Sequence[MemoryView] = (), game_id: str = "g0",
                  grep: GrepFn | None = None) -> AgentOutput:
        """Call decide; if it asked for a grep and grep is available, call it again with the result."""
        first: AgentOutput = await _maybe_await(self.decide(obs, None))
        g = next((a for a in first.actions if isinstance(a, GrepLog)), None)
        if g is None or grep is None:
            return first
        second: AgentOutput = await _maybe_await(self.decide(obs, grep(g)))
        follow = [a for a in second.actions if not isinstance(a, GrepLog)]
        return AgentOutput(
            cot="\n".join(c for c in (first.cot, second.cot) if c) or None,
            note=second.note if second.note is not None else first.note,
            actions=[g, *follow], parse_ok=first.parse_ok and second.parse_ok,
            retries=first.retries + second.retries, errors=first.errors + second.errors,
            llm_call_ids=first.llm_call_ids + second.llm_call_ids)


class _HookResult:
    def __init__(self, events: list[EventBody]) -> None:
        self.events = events


class HookGod:
    """Adapts a legacy god_hook(state, round, next_turn) -> events to the GodLike protocol."""

    def __init__(self, hook: GodHook) -> None:
        self.hook = hook

    def should_wake(self, state: GameState) -> bool:
        """The hook decides itself; always consult it."""
        return True

    async def wake(self, state: GameState) -> _HookResult:
        """Run the hook before slot `next_turn` (= state.turn_index on entry). FROZEN convention that
        runner/wiring.py's _SlotGod adapter relies on: the hook is entered with
        state.turn_index = next_turn - 1; the engine resets it to next_turn afterwards."""
        next_turn = state.turn_index
        state.turn_index = next_turn - 1
        return _HookResult(list(await _maybe_await(self.hook(state, state.round, next_turn))))


class GameEngine:
    """Runs one game. `state` is mutated in place; `snapshots` holds end-of-round deep copies."""

    def __init__(self, cfg: RunConfig, state: GameState,
                 agents: Mapping[AgentId, TurnAgent] | DecideFn, *,
                 god: GodLike | None = None, god_hook: GodHook | None = None,
                 sink: EventSink | None = None, memory: MemoryStore | None = None,
                 on_snapshot: Callable[[GameState], None] | None = None, seed: int | None = None,
                 ledgers: dict[AgentId, list[HistoryItem]] | None = None,
                 counter: TokenCounter | None = None) -> None:
        self.cfg, self.g = cfg, cfg.game
        self.state = state
        if callable(agents) and not isinstance(agents, Mapping):
            shared = DecideAgent(agents)
            self.agents: dict[AgentId, Any] = {a: shared for a in state.agents}
        else:
            self.agents = dict(agents)
        missing = set(state.agents) - set(self.agents)
        if missing:
            raise ValueError(f"no player for agents {sorted(missing)}")
        self.god: GodLike | None = god if god is not None else (HookGod(god_hook) if god_hook else None)
        self.sink: EventSink = sink or MemorySink(game_id=state.game_id)
        self.seed = cfg.run.seed if seed is None else seed
        self.memory = memory or MemoryStore(cfg.reasoning)
        self.on_snapshot = on_snapshot
        self.counter = counter or make_counter(cfg.context.tokenizer)
        self.ledgers: dict[AgentId, list[HistoryItem]] = ledgers or {a: [] for a in state.agents}
        self.obs_turns: dict[AgentId, list[int]] = {a: [] for a in state.agents}   # for grep_log
        self.snapshots: list[GameState] = []
        self.end_reason: str | None = None
        self._started = False

    # ------------------------------------------------------------------ helpers
    def emit(self, bodies: Sequence[EventBody]) -> None:
        """Send event bodies to the sink (which stamps run/game ids and seq)."""
        for b in bodies:
            self.sink.emit(b)

    def _body(self, data: Any, *, actor: str = "SYSTEM", phase: str = "end",
              turn: int | None = None) -> EventBody:
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
        """Turn order of round r: fixed (state.order) or a seeded reshuffle."""
        if self.g.turn_order != "reshuffle":
            return list(self.state.order)
        names = sorted(self.state.agents)
        make_rng(self.seed, self.state.game_id, "order", r).shuffle(names)
        return names

    def scores(self) -> dict[AgentId, float]:
        """Current score per agent."""
        return {a: rules.score(self.state, a) for a in sorted(self.state.agents)}

    def all_done(self) -> bool:
        """Every agent has won or has no open need left."""
        return all(rules.is_done(self.state, a) for a in self.state.agents)

    def _snapshot(self) -> None:
        snap = self.state.model_copy(deep=True)
        self.snapshots.append(snap)
        if self.on_snapshot is not None:
            self.on_snapshot(snap)

    def memory_views(self, agent: AgentId) -> list[MemoryView]:
        """Scratchpad (+ CoT when cot_replay_window > 0) entries the agent is shown this turn."""
        rc, st = self.cfg.reasoning, self.state
        out: list[MemoryView] = []
        if rc.scratchpad.enabled:
            out += self.memory.views(st, agent, "scratchpad", st.round, rc.scratchpad.window)
        if rc.cot_mode != "none" and rc.cot_replay_window > 0:
            out += self.memory.views(st, agent, "cot", st.round, rc.cot_replay_window)
        return out

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> None:
        """Emit game_start and the start snapshot; initialise God's budget. Idempotent."""
        if self._started:
            return
        self._started = True
        st = self.state
        init = getattr(self.god, "init_game", None)
        if init is not None:
            init(st)
        self.emit([EventBody(round=st.round, turn_index=None, phase="setup", actor="SYSTEM", data=GameStartData(
            config_hash=self.cfg.config_hash(), n_agents=len(st.agents), max_rounds=self.g.max_rounds,
            order=list(st.order), agents={a: s.model_copy(deep=True) for a, s in st.agents.items()},
            branch=self.cfg.run.branch, replica=self.cfg.run.replica))])
        self._snapshot()

    async def _god(self, slot: int) -> None:
        """Give God the chance to act before `slot`; its records are stamped with `slot`."""
        if self.god is None:
            return
        self.state.turn_index = slot
        if self.god.should_wake(self.state):
            res = await self.god.wake(self.state)
            self.emit(list(res.events))
        self.state.turn_index = slot

    def _observe(self, agent: AgentId, t: int) -> Observation:
        obs = observe(self.state, agent, self.g, t)
        mark_observed(self.state, agent, t)
        self.obs_turns[agent].append(t)
        return obs

    def _grep_fn(self, agent: AgentId, store: list[GrepResult]) -> GrepFn | None:
        """Per-turn grep callback over the agent's visible log history (None if grep is off)."""
        vl = self.g.view_log
        if not vl.grep_enabled or vl.content == "none":
            return None

        def run(action: GrepLog) -> GrepResult:
            if store:                                  # once per turn
                return store[0]
            res = grep_log(self.state, agent, self.g, action.pattern, self.obs_turns[agent],
                           rounds=action.rounds)
            store.append(res)
            return res
        return run

    async def _act(self, agent: AgentId, obs: Observation) -> tuple[AgentOutput, GrepResult | None]:
        greps: list[GrepResult] = []
        out = await _maybe_await(self.agents[agent].act(
            obs, ledger=list(self.ledgers[agent]), memory=self.memory_views(agent),
            game_id=self.state.game_id, grep=self._grep_fn(agent, greps)))
        return out, (greps[0] if greps else None)

    def _emit_turn(self, agent: AgentId, t: int, obs: Observation, out: AgentOutput) -> None:
        st = self.state
        trace = getattr(self.agents[agent], "last", None)
        self.emit([EventBody(round=st.round, turn_index=t, phase="agents", actor=agent, data=TurnData(
            agent=agent, obs=obs, obs_hash=sha256_hex(canonical_json(obs)),
            prompt_set_hash=getattr(trace, "prompt_set_hash", None),
            prompt_hash=getattr(trace, "prompt_hash", None), llm_call_ids=list(out.llm_call_ids),
            cot=out.cot, note=out.note, actions=list(out.actions), parse_ok=out.parse_ok,
            retries=out.retries, errors=list(out.errors)))])
        bundle = getattr(trace, "bundle", None)
        if bundle is not None and getattr(bundle, "agent", None) == agent:
            self.emit([EventBody(round=st.round, turn_index=t, phase="agents", actor=agent, data=ContextBuiltData(
                agent=agent, policy=bundle.policy, tokens_by_section={s.name: s.tokens for s in bundle.sections},
                tokens_total=bundle.tokens_total, budget=bundle.budget,
                included_item_ids=list(bundle.items), dropped_count=len(bundle.dropped_item_ids)))])

    def _resolve(self, agent: AgentId, t: int, obs: Observation, out: AgentOutput,
                 grep: GrepResult | None) -> None:
        """Log the turn, apply its actions at slot t, write memory, extend the ledger."""
        st = self.state
        st.turn_index = t
        self._emit_turn(agent, t, obs, out)
        results: list[Result] = []
        used, grep_left = 0, grep
        post_at = self._whole_turn_post(out.actions)
        blocked: list[Action] = []
        for i, act in enumerate(out.actions):
            if isinstance(act, GrepLog):                # free: no action slot
                results.append(self._grep_result(agent, act, grep_left))
                grep_left = None                        # a second grep_log in one turn fails
                continue
            if post_at is not None and i != post_at and not isinstance(act, Noop):
                results.append(self._reject(agent, act, BOARD_WHOLE_TURN))   # uses no slot
                blocked.append(act)
                continue
            res = self._apply_one(agent, act, used)
            results.append(res)
            used += 1
            if not res[0] and self.g.turn_mode == "simultaneous" and isinstance(act, (GiveKey, DefectAction)):
                self.emit([rules._notice(st, agent, "system", _conflict_text(act, res[1]))])
        if blocked:
            self.emit([rules._notice(st, agent, "system", _whole_turn_text(blocked))])
        if self.cfg.reasoning.cot_mode != "none" and out.cot:
            _, ev = self.memory.write(st, agent, "cot", st.round, out.cot)
            self.emit([ev])
        if self.cfg.reasoning.scratchpad.enabled and out.note:
            _, ev = self.memory.write(st, agent, "scratchpad", st.round, out.note)
            self.emit([ev])
        self.ledgers[agent] += items_from_observation(obs, self.counter)
        self.ledgers[agent] += own_action_items(agent, st.round, list(out.actions), results, self.counter)

    def _grep_result(self, agent: AgentId, act: GrepLog, grep: GrepResult | None) -> Result:
        ok = grep is not None
        self.emit([self._body(ActionResultData(
            agent=agent, action=act, ok=ok, reason=None if ok else "grep_unavailable",
            n_hits=len(grep.hits) if grep is not None else None),
            actor=agent, phase="resolve", turn=self.state.turn_index)])
        return ok, None if ok else "grep_unavailable"

    def _whole_turn_post(self, actions: Sequence[Action]) -> int | None:
        """Under game.board.post_costs_turn: index of the turn's first post_board, which takes the
        whole turn (None when the option is off or there is no post)."""
        if not self.g.board.post_costs_turn:
            return None
        return next((i for i, a in enumerate(actions) if isinstance(a, PostBoard)), None)

    def _reject(self, agent: AgentId, act: Action, reason: str) -> Result:
        """Emit a failed action_result for `act` without applying it."""
        self.emit([self._body(ActionResultData(agent=agent, action=act, ok=False, reason=reason),
                              actor=agent, phase="resolve", turn=self.state.turn_index)])
        return False, reason

    def _apply_one(self, agent: AgentId, act: Action, used: int) -> Result:
        if used >= self.g.actions_per_turn:
            return self._reject(agent, act, "action_limit")
        _, evs = rules.apply(self.state, agent, act, self.g)
        self.emit(evs)
        first = evs[0].data if evs else None
        if isinstance(first, ActionResultData):
            return first.ok, first.reason
        return True, None

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
                await self._god(t)
                if not self.active(agent):
                    continue
                obs = self._observe(agent, t)
                out, grep = await self._act(agent, obs)
                self._resolve(agent, t, obs, out, grep)
        else:
            s0 = turn_index(r, 0, n)
            await self._god(s0)
            st.turn_index = s0
            actors = [a for a in st.order if self.active(a)]
            obs_by = {a: self._observe(a, s0) for a in actors}
            outs = await asyncio.gather(*(self._act(a, obs_by[a]) for a in actors))
            pos = {a: p for p, a in enumerate(st.order)}
            for a, (out, grep) in zip(actors, outs, strict=True):
                self._resolve(a, turn_index(r, pos[a], n), obs_by[a], out, grep)
        st.turn_index = turn_index(r + 1, 0, n) - 1
        sc = self.scores()
        self.emit([self._body(RoundEndData(state_hash=st.state_hash(), scores=sc,
                                           welfare=sum(sc.values()) / max(len(sc), 1)))])
        self._snapshot()

    def outcome(self) -> Outcome:
        """The game's Outcome from the current state."""
        st = self.state
        sc = self.scores()
        per = {a: AgentOutcome(score=sc[a], won_round=s.won_round, burned=list(s.burned), lost=list(s.lost))
               for a, s in sorted(st.agents.items())}
        n = max(len(per), 1)
        return Outcome(game_id=st.game_id, rounds_played=st.round, end_reason=self.end_reason or "max_rounds",
                       per_agent=per, welfare=sum(sc.values()) / n,
                       win_rate=sum(1 for o in per.values() if o.won_round is not None) / n)

    async def run(self, max_rounds: int | None = None) -> Outcome:
        """Play until max_rounds, all agents done, or BudgetExceeded; emits game_end, returns Outcome.
        Other exceptions from players / God (AuthError, CacheMiss, bugs) propagate."""
        self.start()
        limit = max_rounds or self.g.max_rounds
        try:
            while self.state.round < limit:
                if self.all_done():
                    self.end_reason = "all_done"
                    break
                await self.run_round()
            else:
                self.end_reason = "all_done" if self.all_done() else "max_rounds"
        except BudgetExceeded:
            self.end_reason = "budget_exceeded"
        self.state.done = True
        out = self.outcome()
        self.emit([self._body(GameEndData(outcome=out))])
        return out


BOARD_WHOLE_TURN = "board_post_uses_whole_turn"


def _whole_turn_text(blocked: Sequence[Action]) -> str:
    """Notice for actions dropped because a post_board took the whole turn (board.post_costs_turn)."""
    kinds = ", ".join(a.kind for a in blocked)
    return (f"Your other action(s) this turn ({kinds}) were not done: posting to the public board uses "
            "your whole turn. A direct message costs one action.")


def _conflict_text(act: Action, reason: str | None) -> str:
    """Notice for a failed give/defect in simultaneous mode (the state may have changed since the
    agent observed it: actions resolve in turn-priority order)."""
    what = (f"give_key of info #{act.info_id} to {act.to}" if isinstance(act, GiveKey)
            else f"defect on {act.target} for info #{act.info_id}")
    return (f"Your {what} failed ({reason or 'invalid'}). Actions this round resolved in turn order, "
            "so players before you may have changed the state you saw.")


def play_game(cfg: RunConfig, state: GameState, agents: Mapping[AgentId, TurnAgent] | DecideFn,
              **kw: Any) -> tuple[Outcome, GameEngine]:
    """Synchronous convenience wrapper: run a whole game, return (outcome, engine)."""
    eng = GameEngine(cfg, state, agents, **kw)
    return asyncio.run(eng.run()), eng


def noop_decide(obs: Observation, grep: GrepResult | None = None) -> AgentOutput:
    """Decision stub that does nothing."""
    return AgentOutput(actions=[Noop()])
