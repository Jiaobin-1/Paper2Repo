import hmac
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from app.api import api_router
from app.core.config import get_settings
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

    @app.middleware("http")
    async def require_api_token(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        token = get_settings().api_auth_token
        api_path = request.url.path == "/api" or request.url.path.startswith("/api/")
        guarded = bool(token) and api_path and request.method != "OPTIONS"
        if guarded:
            scheme, _, presented = request.headers.get("authorization", "").partition(" ")
            if scheme.lower() != "bearer" or not hmac.compare_digest(presented, token):
                return JSONResponse(
                    {"detail": "Unauthorized"},
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"},
                )
        return await call_next(request)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "paper2repo-api"}

    app.include_router(api_router)
    return app


app = create_app()
