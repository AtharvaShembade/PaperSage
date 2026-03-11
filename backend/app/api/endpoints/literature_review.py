import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session

from app.models import crud, models
from app.models.database import get_db_session
from app.schemas import schemas
from app.api import deps
from app.services import literature_review_service, ingestion_service

router = APIRouter()


@router.post("/projects/{project_id}/lit-review/search", response_model=schemas.LitReviewSearchResponse)
async def search_papers_for_review(
    project_id: int,
    body: schemas.LitReviewRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        paper_ids, ingestion_tasks = await literature_review_service.search_and_add_papers(
            project_id=project_id,
            question=body.question,
            db=db,
        )

        for paper_id, arxiv_id, pdf_url in ingestion_tasks:
            background_tasks.add_task(
                ingestion_service.process_paper,
                paper_id=paper_id,
                arxiv_id=arxiv_id,
                s2_pdf_url=pdf_url,
            )

        return schemas.LitReviewSearchResponse(
            paper_ids=paper_ids,
            message=f"Added {len(paper_ids)} papers. Ingestion in progress.",
        )
    except Exception as e:
        logging.error(f"Lit review search failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to search and add papers")


@router.post("/projects/{project_id}/lit-review/generate", response_model=schemas.LitReviewGenerateResponse)
async def generate_review(
    project_id: int,
    body: schemas.LitReviewRequest,
    db: Session = Depends(get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Check that project has ready papers
    ready_papers = [p for p in project.papers if p.status == "ready"]
    if not ready_papers:
        raise HTTPException(
            status_code=400,
            detail="No ready papers in this project. Wait for ingestion to complete.",
        )

    try:
        review = await literature_review_service.generate_review(
            project_id=project_id,
            question=body.question,
            db=db,
        )
        return schemas.LitReviewGenerateResponse(review=review)
    except Exception as e:
        logging.error(f"Lit review generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate literature review")
