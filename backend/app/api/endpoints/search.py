from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List
from app.api import deps
from app.services import search_service
from app.schemas import schemas
from app.models import models

router = APIRouter()

@router.get("/")
async def get_search_results(
    q: str = Query(..., min_length = 3, description = "Search query"),
    limit: int = Query(20, gt = 0, le = 100, description = "Maximum number of results to return"),
    current_user: models.User = Depends(deps.get_current_user)
):

    try:
        results = await search_service.search_papers(query = q, limit = limit)
        return results
    
    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = f"Error searching papers: {str(e)}"
        )