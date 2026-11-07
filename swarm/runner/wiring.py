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

        return LoggingClient(FakeLLM(model=model), run.log_llm_call, run_id=run.run_id, backend="fake",
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


async def _play_real(spec: GameSpec, sink: GameWriter, clients: Clients) -> Outcome:
    """ADAPT HERE if the engine/agent/God constructors differ. Assumed (doc §8, peers' code):
      generate_world(cfg.game, seed, game_id) -> GameState                    [swarm.game.world]
      LLMAgent(agent_id, client, cfg, policy=..., counter=...)               [swarm.agents.llm_agent]
      make_god(cfg.god, seed=..., client=...) ; GodRunner(god, cfg.god, memory, max_message_chars=)
      GameEngine(cfg, state, agents, god=runner|None, sink=sink, memory=memory,
                 on_snapshot=sink.snapshot).run() -> Outcome                  [swarm.game.engine]
    """
    from swarm.adversary.base import GodRunner
    from swarm.adversary.llm_god import make_god
    from swarm.agents.llm_agent import LLMAgent
    from swarm.game.engine import GameEngine  # type: ignore[import-not-found]
    from swarm.game.world import generate_world
    from swarm.memory import MemoryStore

    cfg = spec.cfg
    state = generate_world(cfg.game, spec.world_seed, spec.game_id)
    memory = MemoryStore(cfg.reasoning)
    policy = _context_policy(cfg)
    agents = {a: LLMAgent(a, clients.get("agent"), cfg, policy=policy) for a in state.order}
    god = make_god(cfg.god, seed=spec.world_seed, client=clients.get("god"))
    runner = GodRunner(god, cfg.god, memory, max_message_chars=cfg.game.max_message_chars) if god else None

    kwargs: dict[str, Any] = {"god": runner, "sink": sink, "memory": memory}
    params = inspect.signature(GameEngine).parameters
    for name, val in (("on_snapshot", sink.snapshot), ("snapshot", sink.snapshot), ("game_id", spec.game_id)):
        if name in params:
            kwargs[name] = val
    kwargs = {k: v for k, v in kwargs.items() if k in params or any(
        p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())}
    eng = GameEngine(cfg, state, agents, **kwargs)
    outcome = await eng.run()
    return outcome


def _context_policy(cfg: RunConfig) -> Any:
    """context.policy -> policy object (B3/WP13). Falls back to PassthroughPolicy."""
    try:
        from swarm.context import policies  # type: ignore[attr-defined]

        make = getattr(policies, "make_policy", None)
        if make is not None:
            return make(cfg.context)
    except ImportError:
        pass
    from swarm.context.base import PassthroughPolicy

    return PassthroughPolicy()
