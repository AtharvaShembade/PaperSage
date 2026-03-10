import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any

from app.models import crud, models
from app.models.database import get_db_session
from app.schemas import schemas
from app.api import deps
from app.services import rag_service

router = APIRouter()

@router.post("/chat", response_model = schemas.ChatResponse)
async def handle_chat_query(
    chat_request: schemas.ChatRequest,
    db: Session = Depends(get_db_session),
    current_user: models.User = Depends(deps.get_current_user)
) -> Any:

    project_id = chat_request.project_id
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

    try:
        result = await rag_service.answer_question(
            project_id = project_id,
            query = chat_request.query,
            db = db,
            deep = chat_request.deep
        )

        return schemas.ChatResponse(
            answer=result["answer"],
            sources=[schemas.ChatSource(**s) for s in result["sources"]],
            follow_ups=result.get("follow_ups", [])
        )

    except Exception as e:
        logging.error(f"Failed to answer chat query: {e}")
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = f"Failed to answer chat query: {str(e)}"
        )
