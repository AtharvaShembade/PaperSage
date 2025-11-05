from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.models import crud, models
from app.models.database import get_db_session
from app.schemas import schemas
from app.api import deps

# from app.services import analysis_service

router = APIRouter()

@router.get("/projects/{project_id}/analysis", response_model = schemas.GraphResponse)
async def get_citation_graph(
    project_id: int,
    db: Session = Depends(get_db_session),
    current_user: models.User = Depends(deps.get_current_user)
) -> Any:

    project = crud.get_project(db = db, project_id = project_id)
    if not project:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "Project not found"
        )

    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail = "Not authorized to access this project"
        )

    papers = project.papers

    ready_papers = [p for p in papers if p.status == "ready"]

    nodes = []
    paper_ids = set()
    for paper in ready_papers:
        nodes.append({
            "id": paper.external_id,
            "label": paper.title,
            "year": paper.year
        })
        paper_ids.add(paper.external_id)

    edges = []

    return {"nodes": nodes, "edges": edges}

@router.post("/projects/{project_id}/generate-review", status_code = status.HTTP_202_ACCEPTED)
async def start_literrature_review(
    project_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
    current_user: models.User = Depends(deps.get_current_user)
):
    project = crud.get_project(db = db, project_id = project_id)
    if not project:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "Project not found"
        )
    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail = "Not authorized to access this project"
        )
    
    # 2. --- Start Background Task ---
    # In V2, you would replace this with a Celery task to get a task_id
    # background_tasks.add_task(
    #     analysis_service.run_literature_review,
    #     project_id=project.id,
    #     user_id=current_user.id
    # )

    return {"status": "processing", "message": "Literature review generation started."}
 