from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from app.models import crud, models, database
from app.schemas import schemas
from app.api import deps
from app.services import ingestion_service
from app.core.redis import get_redis

router = APIRouter()

async def _invalidate_project_caches(project_id: int) -> None:
    redis = await get_redis()
    if not redis:
        return
    await redis.delete(f"comparison:{project_id}")
    # delete all gaps keys for this project (varies by focus hash)
    keys = await redis.keys(f"gaps:{project_id}:*")
    if keys:
        await redis.delete(*keys)

@router.post("/projects/{project_id}/add-paper", status_code = status.HTTP_202_ACCEPTED)
async def add_paper(
    project_id: int,
    paper_to_add: schemas.PaperCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db_session),
    current_user: models.User = Depends(deps.get_current_user)
):
    project = db.get(models.Project, project_id)
    if not project:
        raise HTTPException(status_code = 404, detail = "Project not found")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code = 403, detail = "Not authorized to add paper to this project")

    db_paper = crud.get_paper(db, paper_to_add.external_id)

    if db_paper:
        crud.link_paper_to_project(db = db, project_id = project_id, paper_id = db_paper.id)
        await _invalidate_project_caches(project_id)
        return {"status": "ok", "message": "Paper already exists in the project"}

    db_paper = crud.create_paper(db, paper = paper_to_add, status = "processing")

    crud.link_paper_to_project(db = db, project_id = project_id, paper_id = db_paper.id)

    background_tasks.add_task(
        ingestion_service.process_paper,
        paper_id   = db_paper.id,
        arxiv_id   = paper_to_add.arxiv_id,
        s2_pdf_url = str(paper_to_add.pdf_url) if paper_to_add.pdf_url else None,
    )
    await _invalidate_project_caches(project_id)

    return {"status": "ok", "message": "Paper added to project."}

@router.delete("/projects/{project_id}/papers/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_paper(
    project_id: int,
    paper_id: int,
    db: Session = Depends(database.get_db_session),
    current_user: models.User = Depends(deps.get_current_user)
):
    project = db.get(models.Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    crud.remove_paper_from_project(db, project_id=project_id, paper_id=paper_id)
    await _invalidate_project_caches(project_id)