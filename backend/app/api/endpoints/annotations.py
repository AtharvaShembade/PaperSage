from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.models import crud, models
from app.models.database import get_db_session
from app.schemas import schemas
from app.api import deps

router = APIRouter()


@router.post("/projects/{project_id}/annotations", response_model=schemas.Annotation, status_code=status.HTTP_201_CREATED)
def create_annotation(
    project_id: int,
    body: schemas.AnnotationCreate,
    db: Session = Depends(get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return crud.create_annotation(db, project_id, body.paper_title, body.chunk_text)


@router.get("/projects/{project_id}/annotations", response_model=List[schemas.Annotation])
def list_annotations(
    project_id: int,
    db: Session = Depends(get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return crud.get_annotations(db, project_id)


@router.patch("/annotations/{annotation_id}", response_model=schemas.Annotation)
def update_annotation(
    annotation_id: int,
    body: schemas.AnnotationUpdate,
    db: Session = Depends(get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    annotation = crud.get_annotation(db, annotation_id)
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")

    project = crud.get_project(db, annotation.project_id)
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return crud.update_annotation(db, annotation_id, body.user_note)


@router.delete("/annotations/{annotation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_annotation(
    annotation_id: int,
    db: Session = Depends(get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    annotation = crud.get_annotation(db, annotation_id)
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")

    project = crud.get_project(db, annotation.project_id)
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    crud.delete_annotation(db, annotation_id)
