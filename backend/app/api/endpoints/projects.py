#creates container

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.models import crud, models
from app.models.database import get_db_session
from app.schemas import schemas
from app.api.deps import get_current_user

router = APIRouter()

#Create project
@router.post("/", response_model = schemas.Project, status_code = status.HTTP_201_CREATED)
def create_project(
    *,
    db: Session = Depends(get_db_session),
    project_in: schemas.ProjectCreate,
    current_user: models.User = Depends(get_current_user)
):
    project = crud.create_project(db = db, project = project_in, user_id = current_user.id)
    return project


#Get projects
@router.get("/", response_model=List[schemas.ProjectDetail])
def read_projects(
    *,
    db: Session = Depends(get_db_session),
    current_user: models.User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    projects = crud.get_projects_by_user(db = db, user_id = current_user.id, skip = skip, limit = limit)
    return projects


#Get project by id
@router.get("/{project_id}", response_model=schemas.ProjectDetail)
def read_project(
    *,
    db: Session = Depends(get_db_session),
    project_id: int,
    current_user: models.User = Depends(get_current_user)
):
    """
    Gets the details for a single project, including its papers.
    """
    project = crud.get_project(db=db, project_id=project_id)
    
    # Check 1: Does the project exist?
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check 2: Does this user own the project?
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this project")
        
    return project


#Delete project
@router.delete("/{project_id}", response_model=schemas.Project)
def delete_project(
    *,
    db: Session = Depends(get_db_session),
    project_id: int,
    current_user: models.User = Depends(get_current_user)
):
    """
    Deletes an entire project and all its associated data.
    """
    project = crud.get_project(db=db, project_id=project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this project")
    
    crud.delete_project(db=db, project_id=project_id)
    
    return project