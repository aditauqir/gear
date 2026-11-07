"""LLM-call log (WP5): a thin LLMClient wrapper that records one `LLMCall` per chat() call.

Use it when the WP2 middleware stack has no Accounting layer of its own (or pass
`RunWriter.log_llm_call` as that layer's callback instead; do not do both, or calls are logged twice).
Requests carry messages + sampling only (never headers or keys); every line is redacted on write.
"""

from __future__ import annotations

from collections.abc import Callable

from swarm.rng import canonical_json, sha256_hex
from swarm.schema import ChatRequest, ChatResponse, LLMCall

OnCall = Callable[[LLMCall], None]


def cache_key(backend: str, model: str, req: ChatRequest) -> str:
    """Same recipe as the doc (§5): model, backend and the full sampling dict (incl. messages, seed)."""
    return sha256_hex(canonical_json({"backend": backend, "model": model, **req.sampling()}))


class LoggingClient:
    """Wraps any LLMClient. Errors are logged (type + message, redacted) and re-raised."""

    def __init__(self, inner: object, on_call: OnCall, *, run_id: str, backend: str, model: str) -> None:
        self.inner, self.on_call, self.run_id = inner, on_call, run_id
        self.backend, self.model = backend, model

    def __repr__(self) -> str:  # never expose the inner client's config (may hold a key)
        return f"LoggingClient(backend={self.backend!r}, model={self.model!r})"

    async def chat(self, req: ChatRequest) -> ChatResponse:
        key = cache_key(self.backend, self.model, req)
        try:
            resp = await self.inner.chat(req)  # type: ignore[attr-defined]
        except Exception as e:
            self.on_call(LLMCall(run_id=self.run_id, backend=self.backend, model=self.model,
                                 cache_key=key, request=req, error=f"{type(e).__name__}: {e}"))
            raise
        self.on_call(LLMCall(run_id=self.run_id, backend=resp.backend or self.backend,
                             model=resp.model or self.model, cache_key=key, request=req, response=resp))
        return resp
