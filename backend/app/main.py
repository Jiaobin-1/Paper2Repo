from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.lifecycle import lifespan


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

    app.include_router(api_router)
    return app


app = create_app()
