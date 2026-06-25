from __future__ import annotations

import uuid
from typing import Any

from app.repositories.connection import get_connection, utc_now


def save_llm_usage_events(run_id: str, events: list[dict[str, Any]]) -> None:
    if not events:
        return
    with get_connection() as conn:
        conn.executemany(
            """
            INSERT INTO llm_usage_events (
                id, run_id, model, mode, operation, input_tokens, output_tokens,
                total_tokens, estimated_cost_usd, latency_ms, attempts, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    str(uuid.uuid4()),
                    run_id,
                    str(event.get("model") or "unknown"),
                    str(event.get("mode") or "unknown"),
                    str(event.get("operation") or "unknown"),
                    int(event.get("input_tokens") or 0),
                    int(event.get("output_tokens") or 0),
                    int(event.get("total_tokens") or 0),
                    float(event.get("estimated_cost_usd") or 0),
                    float(event.get("latency_ms") or 0),
                    int(event.get("attempts") or 1),
                    utc_now(),
                )
                for event in events
            ],
        )


def get_llm_usage_summary(run_id: str) -> dict[str, Any]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT model, mode, operation, input_tokens, output_tokens, total_tokens,
                   estimated_cost_usd, latency_ms, attempts, created_at
            FROM llm_usage_events
            WHERE run_id = ?
            ORDER BY created_at ASC
            """,
            (run_id,),
        ).fetchall()
    events = [dict(row) for row in rows]
    return {
        "run_id": run_id,
        "call_count": len(events),
        "input_tokens": sum(event["input_tokens"] for event in events),
        "output_tokens": sum(event["output_tokens"] for event in events),
        "total_tokens": sum(event["total_tokens"] for event in events),
        "estimated_cost_usd": round(sum(event["estimated_cost_usd"] for event in events), 8),
        "latency_ms": round(sum(event["latency_ms"] for event in events), 2),
        "events": events,
    }
