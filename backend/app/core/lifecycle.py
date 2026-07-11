import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app.core.database import init_db
from app.services.analysis_runner import (
    recover_analysis_jobs_forever,
    start_analysis_dispatcher,
    start_recoverable_analysis_jobs,
    stop_analysis_dispatcher,
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    start_analysis_dispatcher()
    start_recoverable_analysis_jobs()
    recovery_task = asyncio.create_task(recover_analysis_jobs_forever())
    try:
        yield
    finally:
        recovery_task.cancel()
        with suppress(asyncio.CancelledError):
            await recovery_task
        stop_analysis_dispatcher()
