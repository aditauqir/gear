"""OpenRouter preset (https://openrouter.ai/api/v1). OFF by default (`llm.openrouter.enabled`).

- Key: env OPENROUTER_API_KEY, else the raw-key file (`load_key()`; default
  secrets.DEFAULT_OPENROUTER_KEY_FILE). The key lives only inside the client as a SecretStr; it
  is registered with secrets.redact() and is never printed, logged, cached or recorded.
- `req.thinking` maps to `reasoning: {enabled: bool}`; usage/cost via `usage: {include: true}`.
- Spend caps, both checked BEFORE each call against a worst-case estimate:
    global  `GlobalLedger` over runs/openrouter_ledger.jsonl (append-only, fcntl.flock), default $2
    run     `RunBudget` (llm.budget_usd), shared by every client of one run
  Exceeding either raises BudgetExceeded. Actual cost (provider-reported, else the price table)
  is appended to the ledger after the call.

Imports: config, llm.base, llm.cache, llm.openai_compat, llm.secrets (key loading is WP0's).
"""

from __future__ import annotations

import fcntl
import json
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import httpx
from pydantic import SecretStr

from swarm.config import DEFAULT_OPENROUTER_MODEL, REPO_ROOT, OpenRouterCfg, RetryCfg
from swarm.llm.base import BudgetExceeded, ChatRequest, ChatResponse, LLMError, Usage
from swarm.llm.cache import ResponseCache
from swarm.llm.openai_compat import OpenAICompatClient, Recorder
from swarm.llm.secrets import DEFAULT_OPENROUTER_KEY_FILE, OPENROUTER_ENV, load_openrouter_key

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_LEDGER = REPO_ROOT / "runs" / "openrouter_ledger.jsonl"
GLOBAL_CAP_USD = 2.0


def load_key(key_file: str | Path | None = DEFAULT_OPENROUTER_KEY_FILE, *,
             env: Mapping[str, str] | None = None) -> SecretStr | None:
    """Env OPENROUTER_API_KEY first, else the raw-key file. Returns a masked SecretStr or None."""
    return load_openrouter_key(key_file, env=env, env_var=OPENROUTER_ENV)


def estimate_cost(req: ChatRequest, price_in_per_mtok: float, price_out_per_mtok: float) -> float:
    """Worst case: prompt_chars/3.5 tokens in, max_tokens out."""
    chars = sum(len(m.content) for m in req.messages)
    return (chars / 3.5) * price_in_per_mtok / 1e6 + req.max_tokens * price_out_per_mtok / 1e6


class RunBudget:
    """Per-run paid-spend cap (llm.budget_usd). In-process only; share one instance per run."""

    def __init__(self, cap_usd: float) -> None:
        self.cap = cap_usd
        self.spent = 0.0
        self.reserved = 0.0

    def reserve(self, estimate: float) -> None:
        """Raise BudgetExceeded("run") if spent + reserved + estimate > cap, else reserve it."""
        if self.spent + self.reserved + estimate > self.cap:
            raise BudgetExceeded("run", self.spent + self.reserved, estimate, self.cap)
        self.reserved += estimate

    def settle(self, estimate: float, actual: float) -> None:
        """Release the reservation and add the actual cost."""
        self.reserved = max(0.0, self.reserved - estimate)
        self.spent += actual


class GlobalLedger:
    """Append-only JSONL ledger of paid calls across runs and processes: {ts, run_id, call_id, model,
    cost_usd}. total() sums it under a shared flock; record() appends under an exclusive flock."""

    def __init__(self, path: str | Path = DEFAULT_LEDGER, cap_usd: float = GLOBAL_CAP_USD) -> None:
        self.path = Path(path)
        self.cap = cap_usd
        self.reserved = 0.0

    def total(self) -> float:
        """Sum of cost_usd over the ledger file (0 if missing)."""
        if not self.path.is_file():
            return 0.0
        tot = 0.0
        with open(self.path, encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            try:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        tot += float(json.loads(line).get("cost_usd") or 0.0)
                    except (ValueError, AttributeError):
                        continue
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
        return tot

    def reserve(self, estimate: float) -> None:
        """Raise BudgetExceeded("global") if ledger total + reserved + estimate > cap, else reserve it."""
        spent = self.total() + self.reserved
        if spent + estimate > self.cap:
            raise BudgetExceeded("global", spent, estimate, self.cap)
        self.reserved += estimate

    def record(self, *, run_id: str, call_id: str, model: str, cost_usd: float, estimate: float) -> None:
        """Append one paid call and release its reservation."""
        self.reserved = max(0.0, self.reserved - estimate)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps({"ts": time.time(), "run_id": run_id, "call_id": call_id, "model": model,
                           "cost_usd": cost_usd}) + "\n"
        with open(self.path, "a", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                f.write(line)
                f.flush()
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def release(self, estimate: float) -> None:
        """Drop a reservation for a call that failed (nothing recorded)."""
        self.reserved = max(0.0, self.reserved - estimate)


class OpenRouterClient(OpenAICompatClient):
    """Paid OpenRouter backend. Construct with enabled=True (mirrors llm.openrouter.enabled)."""

    backend = "openrouter"

    def __init__(self, *, enabled: bool = False, api_key: SecretStr | None = None,
                 base_url: str = DEFAULT_BASE_URL, model: str = DEFAULT_OPENROUTER_MODEL,
                 max_concurrency: int = 8, price_in_per_mtok: float = 1.0, price_out_per_mtok: float = 4.0,
                 ledger: GlobalLedger | None = None, run_budget: RunBudget | None = None,
                 retry: RetryCfg | None = None, cache: ResponseCache | None = None,
                 recorder: Recorder | None = None, run_id: str = "",
                 transport: httpx.AsyncBaseTransport | None = None, sleep: Any = None) -> None:
        if not enabled:
            raise LLMError("OpenRouter is disabled: set llm.openrouter.enabled=true to use it")
        if api_key is None:
            api_key = load_key()
        if api_key is None:
            raise LLMError(f"OpenRouter key not found: set {OPENROUTER_ENV} or provide the key file")
        super().__init__(base_url=base_url, model=model, api_key=api_key, max_concurrency=max_concurrency,
                         retry=retry, cache=cache, recorder=recorder, run_id=run_id, transport=transport,
                         sleep=sleep)
        self.price_in = price_in_per_mtok
        self.price_out = price_out_per_mtok
        self.ledger = ledger or GlobalLedger()
        self.run_budget = run_budget

    @classmethod
    def from_cfg(cls, cfg: OpenRouterCfg, *, model: str | None = None, budget_usd: float | None = None,
                 run_budget: RunBudget | None = None, retry: RetryCfg | None = None,
                 cache: ResponseCache | None = None, recorder: Recorder | None = None,
                 run_id: str = "", api_key: SecretStr | None = None) -> OpenRouterClient:
        """Build from cfg.llm.openrouter; raises LLMError unless enabled. Relative ledger paths resolve against the repo root."""
        ledger_path = Path(cfg.ledger_path)
        if not ledger_path.is_absolute():
            ledger_path = REPO_ROOT / ledger_path
        if run_budget is None and budget_usd is not None:
            run_budget = RunBudget(budget_usd)
        return cls(enabled=cfg.enabled, api_key=api_key, base_url=cfg.base_url, model=model or cfg.model,
                   max_concurrency=cfg.max_concurrency, price_in_per_mtok=cfg.price_in_per_mtok,
                   price_out_per_mtok=cfg.price_out_per_mtok,
                   ledger=GlobalLedger(ledger_path, cfg.global_cap_usd), run_budget=run_budget,
                   retry=retry, cache=cache, recorder=recorder, run_id=run_id)

    def _headers(self) -> dict[str, str]:
        h = super()._headers()
        h["X-Title"] = "swarm-keys-and-god"
        return h

    def _extra_body(self, req: ChatRequest) -> dict[str, Any]:
        return {"reasoning": {"enabled": bool(req.thinking)}, "usage": {"include": True}}

    def _cost(self, data: dict[str, Any], usage: Usage) -> float:
        reported = (data.get("usage") or {}).get("cost")
        if reported is not None:
            try:
                return float(reported)
            except (TypeError, ValueError):
                pass
        return (usage.prompt_tokens * self.price_in + usage.completion_tokens * self.price_out) / 1e6

    async def _before_call(self, req: ChatRequest) -> Any:
        est = estimate_cost(req, self.price_in, self.price_out)
        self.ledger.reserve(est)
        if self.run_budget is not None:
            try:
                self.run_budget.reserve(est)
            except BudgetExceeded:
                self.ledger.release(est)
                raise
        return est

    async def _after_call(self, req: ChatRequest, token: Any, resp: ChatResponse | None) -> None:
        est = float(token or 0.0)
        actual = resp.cost_usd if resp is not None else 0.0
        if resp is not None:
            self.ledger.record(run_id=self.run_id, call_id=req.call_id, model=self.model,
                               cost_usd=actual, estimate=est)
        else:
            self.ledger.release(est)
        if self.run_budget is not None:
            self.run_budget.settle(est, actual)
