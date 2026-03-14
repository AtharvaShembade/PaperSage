import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.models import crud, models
from app.models.database import get_db_session
from app.schemas import schemas
from app.api import deps

router = APIRouter()


@router.get("/projects/{project_id}/chat-sessions", response_model=List[schemas.ChatSessionResponse])
def list_chat_sessions(
    project_id: int,
    db: Session = Depends(get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return crud.get_chat_sessions(db, project_id=project_id, user_id=current_user.id)


@router.post("/projects/{project_id}/chat-sessions", response_model=schemas.ChatSessionResponse)
def create_chat_session(
    project_id: int,
    body: schemas.ChatSessionCreate,
    db: Session = Depends(get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return crud.create_chat_session(db, project_id=project_id, user_id=current_user.id, name=body.name)


@router.patch("/chat-sessions/{session_id}", response_model=schemas.ChatSessionResponse)
def update_chat_session(
    session_id: int,
    body: schemas.ChatSessionUpdate,
    db: Session = Depends(get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    session = crud.get_chat_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return crud.update_chat_session(db, session_id, name=body.name, messages=body.messages)


@router.delete("/chat-sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_session(
    session_id: int,
    db: Session = Depends(get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    session = crud.get_chat_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    crud.delete_chat_session(db, session_id)
