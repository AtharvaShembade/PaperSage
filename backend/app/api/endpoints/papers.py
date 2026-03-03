from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from app.models import crud, models, database
from app.schemas import schemas
from app.api import deps
from app.services import ingestion_service

router = APIRouter()

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
        return {"status": "ok", "message": "Paper already exists in the project"}

    db_paper = crud.create_paper(db, paper = paper_to_add, status = "processing")

    crud.link_paper_to_project(db = db, project_id = project_id, paper_id = db_paper.id)

    background_tasks.add_task(
        ingestion_service.process_paper,
        paper_id   = db_paper.id,
        arxiv_id   = paper_to_add.arxiv_id,
        s2_pdf_url = str(paper_to_add.pdf_url) if paper_to_add.pdf_url else None,
    )

    return {"status": "ok", "message": "Paper added to project."}