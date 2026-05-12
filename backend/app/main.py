from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_llm import router as llm_router
from app.api.routes_papers import router as papers_router
from app.api.routes_runs import router as runs_router
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Paper2Repo API",
        description="AI paper understanding and reproduction planning MVP.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "paper2repo-api"}

    app.include_router(papers_router, prefix="/api")
    app.include_router(runs_router, prefix="/api")
    app.include_router(llm_router, prefix="/api")
    return app


app = create_app()
