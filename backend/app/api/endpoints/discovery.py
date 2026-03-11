import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models import crud, models
from app.models.database import get_db_session
from app.api import deps
from app.services import discovery_service

router = APIRouter()


@router.get("/projects/{project_id}/discover")
async def discover_related_papers(
    project_id: int,
    db: Session = Depends(get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if not project.papers:
        raise HTTPException(status_code=400, detail="Add papers to the project first")

    try:
        results = await discovery_service.get_related_papers(project_id=project_id, db=db)
        return results
    except Exception as e:
        logging.error(f"Discovery failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to discover related papers")
