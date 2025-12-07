from fastapi import APIRouter

from .endpoints import projects, papers, rag, analysis, search

router = APIRouter()

router.include_router(projects.router, prefix="/projects", tags=["projects"])
router.include_router(papers.router, prefix="/papers", tags=["papers"])
router.include_router(rag.router, prefix="/rag", tags=["rag"])
router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
router.include_router(search.router, prefix="/search", tags=["search"])