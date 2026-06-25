from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, cast

from app.core.config import get_settings
from app.core.database import save_llm_usage_events

logger = logging.getLogger(__name__)


@dataclass
class UsageSession:
    run_id: str
    events: list[dict[str, Any]] = field(default_factory=list)


_current_session: ContextVar[UsageSession | None] = ContextVar("paper2repo_llm_usage_session", default=None)


@contextmanager
def track_llm_usage(run_id: str) -> Iterator[None]:
    existing = _current_session.get()
    if existing is not None and existing.run_id == run_id:
        yield
        return

    session = UsageSession(run_id=run_id)
    token = _current_session.set(session)
    try:
        yield
    finally:
        _current_session.reset(token)
        if session.events:
            try:
                save_llm_usage_events(run_id, session.events)
            except Exception:
                logger.warning("Failed to persist LLM usage for run %s", run_id, exc_info=True)


def record_llm_usage(meta: dict[str, Any]) -> None:
    session = _current_session.get()
    if session is None:
        return

    raw_usage = meta.get("usage")
    usage = cast(dict[str, Any], raw_usage) if isinstance(raw_usage, dict) else {}
    input_tokens = _int_value(usage, "input_tokens", "prompt_tokens")
    output_tokens = _int_value(usage, "output_tokens", "completion_tokens")
    total_tokens = _int_value(usage, "total_tokens") or input_tokens + output_tokens
    settings = get_settings()
    estimated_cost = (
        input_tokens * max(0.0, settings.llm_input_cost_per_million)
        + output_tokens * max(0.0, settings.llm_output_cost_per_million)
    ) / 1_000_000

    session.events.append(
        {
            "model": str(meta.get("model") or "unknown"),
            "mode": str(meta.get("mode") or "unknown"),
            "operation": str(meta.get("schema") or "unknown"),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": round(estimated_cost, 8),
            "latency_ms": float(meta.get("latency_ms") or 0),
            "attempts": int(meta.get("attempts") or 1),
        }
    )


def _int_value(usage: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = usage.get(key)
        if isinstance(value, int):
            return max(0, value)
        if isinstance(value, float):
            return max(0, int(value))
    return 0
