from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_papers import router as papers_router
from app.api.routes_runs import router as runs_router
from app.core.database import init_db


def create_app() -> FastAPI:
    app = FastAPI(
        title="Paper2Repo API",
        description="AI paper understanding and reproduction planning MVP.",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def on_startup() -> None:
        init_db()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "paper2repo-api"}

    app.include_router(papers_router, prefix="/api")
    app.include_router(runs_router, prefix="/api")
    return app


app = create_app()
