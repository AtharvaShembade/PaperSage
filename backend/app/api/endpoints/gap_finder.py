import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models import crud, models
from app.models.database import get_db_session
from app.schemas import schemas
from app.api import deps
from app.services import gap_finder_service

router = APIRouter()


@router.post("/projects/{project_id}/gap-analysis", response_model=schemas.GapAnalysisResponse)
async def run_gap_analysis(
    project_id: int,
    body: schemas.GapFinderRequest,
    db: Session = Depends(get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    ready_papers = [p for p in project.papers if p.status == "ready"]
    if not ready_papers:
        raise HTTPException(
            status_code=400,
            detail="No ready papers in this project. Wait for ingestion to complete.",
        )

    try:
        result = await gap_finder_service.run_gap_analysis(
            project_id=project_id,
            db=db,
            focus=body.focus or None,
        )
        return result
    except Exception as e:
        logging.error(f"Gap analysis failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to run gap analysis")
