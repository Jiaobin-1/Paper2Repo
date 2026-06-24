from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.database import init_db
from app.services.analysis_runner import start_recoverable_analysis_jobs


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    start_recoverable_analysis_jobs()
    yield
