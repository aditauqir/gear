"""THE integration point (WP9). Everything the runner needs from engine / agents / God / LLM lives
here, so the integrator adapts one file when a builder's interface differs from the doc.

    clients = build_clients(cfg, run_writer)                 # once per run, shared by all games
    outcome = await play_game(spec, game_writer, clients)    # one game (any branch)
    await close_clients(clients)

Engines:
    "synth": swarm.runner.synth (no LLM, deterministic; for dry runs and tests)
    "real" : swarm.game.engine.GameEngine + LLMAgent + ScriptedGod/LLMGod via GodRunner

LLM-call logging: B2's clients take `recorder=` (called once per call with an LLMCall, cache hits
included); we pass `RunWriter.log_llm_call`, which routes to the current game's llm_calls.jsonl via a
contextvar. The fake backend has no recorder, so it is wrapped in runlog.LoggingClient instead.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from swarm.config import REPO_ROOT, RunConfig
from swarm.runlog.llmlog import LoggingClient
from swarm.runlog.writer import GameWriter, RunWriter
from swarm.runner.spec import GameSpec
from swarm.schema import Outcome


@dataclass
class Clients:
    by_role: dict[str, Any] = field(default_factory=dict)
    closers: list[Any] = field(default_factory=list)

    def get(self, role: str) -> Any:
        return self.by_role.get(role)


def _abs(p: str) -> Path:
    q = Path(p)
    return q if q.is_absolute() else REPO_ROOT / q


def _build_client(cfg: RunConfig, role: str, run: RunWriter, cache: Any) -> Any:
    backend, model = cfg.model_for(role)
    if backend == "fake":
        from swarm.llm.base import FakeLLM
        from swarm.runner.fake_policy import smart_fake_policy

        return LoggingClient(FakeLLM(policy=smart_fake_policy, model=model), run.log_llm_call, run_id=run.run_id, backend="fake",
                             model=model)
    if backend == "vllm":
        from swarm.llm.vllm import VLLMClient

        return VLLMClient.from_cfg(cfg.llm.vllm, model=model, retry=cfg.llm.retry, cache=cache,
                                   recorder=run.log_llm_call, run_id=run.run_id)
    if backend == "openrouter":
        from swarm.llm.openrouter import GlobalLedger, OpenRouterClient, RunBudget, load_key

        o = cfg.llm.openrouter
        return OpenRouterClient(enabled=o.enabled, api_key=load_key(), base_url=o.base_url, model=model,
                                max_concurrency=o.max_concurrency, price_in_per_mtok=o.price_in_per_mtok,
                                price_out_per_mtok=o.price_out_per_mtok,
                                ledger=GlobalLedger(_abs(o.ledger_path), o.global_cap_usd),
                                run_budget=RunBudget(cfg.llm.budget_usd), retry=cfg.llm.retry, cache=cache,
                                recorder=run.log_llm_call, run_id=run.run_id)
    raise ValueError(f"unknown backend {backend!r}")


def build_clients(cfg: RunConfig, run: RunWriter, engine: str = "real") -> Clients:
    """One client per (role) shared across games (shared semaphores => vLLM batches across games)."""
    out = Clients()
    if engine == "synth":
        return out
    cache = None
    if cfg.llm.cache.mode != "off":
        from swarm.llm.cache import ResponseCache

        path = _abs(cfg.llm.cache.path)
        path.parent.mkdir(parents=True, exist_ok=True)
        cache = ResponseCache(path, cfg.llm.cache.mode)
    roles = ["agent"] + (["god"] if cfg.god.kind == "llm" else [])
    built: dict[tuple[str, str], Any] = {}
    for role in roles:
        key = cfg.model_for(role)
        if key not in built:
            built[key] = _build_client(cfg, role, run, cache)
            out.closers.append(built[key])
        out.by_role[role] = built[key]
    return out


async def close_clients(clients: Clients) -> None:
    for c in clients.closers:
        inner = getattr(c, "inner", c)
        close = getattr(inner, "aclose", None)
        if close is not None:
            res = close()
            if inspect.isawaitable(res):
                await res


# --------------------------------------------------------------------------- one game
async def play_game(spec: GameSpec, sink: GameWriter, clients: Clients, engine: str = "real") -> Outcome:
    if engine == "synth":
        from swarm.runner.synth import play_synth

        return await play_synth(spec, sink)
    return await _play_real(spec, sink, clients)


class LedgerSink:
    """EventSink wrapper that keeps the engine-owned per-agent ledgers (CONTRACTS §1).

    Ledgers live outside GameState and are rebuilt from the event stream: a `turn` event adds the
    items of the observation it logs (items_from_observation, the only constructor), and the
    matching `action_result` events add the agent's own action items. Forwards everything."""

    def __init__(self, inner: Any, counter: Any = None) -> None:
        self.inner, self.counter = inner, counter
        self.ledgers: dict[str, list[Any]] = {}

    def emit(self, body: Any) -> Any:
        from swarm.context.base import items_from_observation, own_action_items

        ev = self.inner.emit(body)
        d = body.data
        if d.type == "turn":
            self.ledgers.setdefault(d.agent, []).extend(items_from_observation(d.obs, self.counter))
        elif d.type == "action_result" and d.action.kind != "grep_log":
            self.ledgers.setdefault(d.agent, []).extend(
                own_action_items(d.agent, body.round, [d.action], [(d.ok, d.reason)], self.counter))
        return ev

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)


class OracleClient:
    """Per-game LLMClient wrapper: every agent-bound ChatRequest is scanned by the LeakOracle BEFORE
    it is sent (a TruthLeak aborts the game, so a leak can never be silently logged as a result)."""

    def __init__(self, inner: Any, oracle: Any) -> None:
        self.inner, self.oracle = inner, oracle

    async def chat(self, req: Any) -> Any:
        self.oracle.assert_clean(req)
        return await self.inner.chat(req)


class _SlotGod:
    """Adapter between the engine's god_hook timing and GodRunner's.

    The engine calls the hook with state.turn_index = next_turn - 1 (so forged DMs are stamped like
    the previous slot and are visible at next_turn). ScriptedGod schedules by the slot ABOUT to be
    played. We expose next_turn while God decides, then restore next_turn - 1 before powers apply."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.name = getattr(inner, "name", "god")
        self.next_turn = 0

    def wakes_at(self, state: Any) -> bool:
        return bool(self.inner.wakes_at(state))

    async def step(self, state: Any, view: Any) -> list[Any]:
        try:
            return list(await self.inner.step(state, view))
        finally:
            state.turn_index = self.next_turn - 1


def make_god_hook(runner: Any, slot_god: _SlotGod) -> Any:
    """-> god_hook(state, round, next_turn) for GameEngine."""

    async def hook(state: Any, r: int, next_turn: int) -> list[Any]:
        slot_god.next_turn = next_turn
        state.turn_index = next_turn
        try:
            if not runner.should_wake(state):
                return []
            res = await runner.wake(state)
            return list(res.events)
        finally:
            state.turn_index = next_turn - 1

    return hook


def make_decide(agents: dict[str, Any], state: Any, memory: Any, ledgers: LedgerSink, cfg: RunConfig,
                game_id: str, engine_ref: list[Any]) -> Any:
    """-> decide(obs, grep) for GameEngine. LLMAgent runs the grep follow-up itself (via a callback),
    so the engine's second decide() call just returns the follow-up actions already chosen."""
    from swarm.game.observe import grep_log

    pending: dict[str, Any] = {}

    async def decide(obs: Any, grep: Any = None) -> Any:
        from swarm.schema import AgentOutput, GrepLog

        a = obs.agent
        if grep is not None and a in pending:
            out = pending.pop(a)
            return AgentOutput(cot=None, note=None, actions=[x for x in out.actions if not isinstance(x, GrepLog)],
                               parse_ok=out.parse_ok)
        mem = []
        sp = cfg.reasoning.scratchpad
        if sp.enabled:
            mem += memory.views(state, a, "scratchpad", obs.round, sp.window)
        if cfg.reasoning.cot_mode != "none" and cfg.reasoning.cot_replay_window > 0:
            mem += memory.views(state, a, "cot", obs.round - 1, cfg.reasoning.cot_replay_window)

        def grep_fn(g: Any) -> Any:
            eng = engine_ref[0]
            return grep_log(state, a, cfg.game, g.pattern, eng.obs_turns[a], rounds=g.rounds)

        out = await agents[a].act(obs, ledger=ledgers.ledgers.get(a, []), memory=mem, game_id=game_id,
                                  grep=grep_fn)
        if any(isinstance(x, GrepLog) for x in out.actions):
            pending[a] = out
        return out

    return decide


async def _play_real(spec: GameSpec, sink: GameWriter, clients: Clients) -> Outcome:
    """World + MemoryStore + LLMAgents + (ScriptedGod via GodRunner) + GameEngine, all events through
    LeakOracle-observing and ledger-keeping sink wrappers; every agent request leak-checked."""
    from swarm.adversary.base import GodRunner
    from swarm.adversary.llm_god import make_god
    from swarm.agents.llm_agent import LLMAgent, default_counter
    from swarm.context.leak_oracle import LeakOracle
    from swarm.game.engine import GameEngine
    from swarm.game.world import generate_world
    from swarm.memory import MemoryStore

    cfg = spec.cfg
    state = generate_world(cfg.game, spec.world_seed, spec.game_id)
    memory = MemoryStore(cfg.reasoning)
    oracle = LeakOracle(enabled=not cfg.game.view_log.reveal_provenance)
    counter = default_counter(cfg)
    ledger_sink = LedgerSink(oracle.wrap(sink), counter)
    client = OracleClient(clients.get("agent"), oracle)
    agents = {a: LLMAgent(a, client, cfg, counter=counter) for a in state.order}   # policy: make_policy
    god = make_god(cfg.god, seed=spec.world_seed, client=clients.get("god"))
    hook = None
    if god is not None:
        slot = _SlotGod(god)
        runner = GodRunner(slot, cfg.god, memory, max_message_chars=cfg.game.max_message_chars)
        runner.init_game(state)
        hook = make_god_hook(runner, slot)
    engine_ref: list[Any] = []
    decide = make_decide(agents, state, memory, ledger_sink, cfg, spec.game_id, engine_ref)
    eng = GameEngine(cfg, state, decide, god_hook=hook, sink=ledger_sink, seed=spec.world_seed, memory=memory)
    engine_ref.append(eng)
    _orig_round = eng.run_round

    async def run_round_snap() -> None:
        await _orig_round()
        sink.snapshot(eng.snapshots[-1])

    eng.run_round = run_round_snap  # type: ignore[method-assign]
    sink.snapshot(state.model_copy(deep=True))
    outcome = await eng.run()
    sink.write_meta(leak_checked=oracle.n_checked, leak_hits=len(oracle.hits))
    return outcome
