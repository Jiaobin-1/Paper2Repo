from fastapi import APIRouter

from app.api.routes_arxiv import router as arxiv_router
from app.api.routes_citations import router as citations_router
from app.api.routes_compare import router as compare_router
from app.api.routes_knowledge import router as knowledge_router
from app.api.routes_llm import router as llm_router
from app.api.routes_papers import router as papers_router
from app.api.routes_pwc import router as pwc_router
from app.api.routes_qa import router as qa_router
from app.api.routes_runs import router as runs_router
from app.api.routes_settings import router as settings_router
from app.api.routes_storage import router as storage_router

api_router = APIRouter(prefix="/api")

api_router.include_router(papers_router)
api_router.include_router(arxiv_router)
api_router.include_router(runs_router)
api_router.include_router(citations_router)
api_router.include_router(llm_router)
api_router.include_router(settings_router)
api_router.include_router(storage_router)
api_router.include_router(qa_router)
api_router.include_router(compare_router)
api_router.include_router(knowledge_router)
api_router.include_router(pwc_router)
