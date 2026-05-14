from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_arxiv import router as arxiv_router
from app.api.routes_citations import router as citations_router
from app.api.routes_compare import router as compare_router
from app.api.routes_knowledge import router as knowledge_router
from app.api.routes_llm import router as llm_router
from app.api.routes_papers import router as papers_router
from app.api.routes_papers import start_recoverable_analysis_jobs
from app.api.routes_pwc import router as pwc_router
from app.api.routes_qa import router as qa_router
from app.api.routes_runs import router as runs_router
from app.api.routes_settings import router as settings_router
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    start_recoverable_analysis_jobs()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Paper2Repo API",
        description=(
            "AI paper understanding and reproduction planning tool. "
            "Upload a PDF, run an 11-node analysis pipeline, "
            "and generate structured Markdown/PDF reproduction reports with Q&A support."
        ),
        version="0.2.0",
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
    app.include_router(arxiv_router, prefix="/api")
    app.include_router(runs_router, prefix="/api")
    app.include_router(citations_router, prefix="/api")
    app.include_router(llm_router, prefix="/api")
    app.include_router(settings_router, prefix="/api")
    app.include_router(qa_router, prefix="/api")
    app.include_router(compare_router, prefix="/api")
    app.include_router(knowledge_router, prefix="/api")
    app.include_router(pwc_router, prefix="/api")
    return app


app = create_app()
