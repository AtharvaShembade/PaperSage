from fastapi import Request, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from supabase import create_client, Client

from app.core.config import settings
from app.models import crud, models
from app.models.database import get_db_session

try:
    supabase: Client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY
    )
except Exception as e:
    raise RuntimeError(f"Failed to initialize Supabase client: {str(e)}")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl = "token")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db_session)
) -> models.User:
    try:
        auth_user = supabase.auth.get_user(token)

        if not auth_user or not auth_user.user:
            raise HTTPException(
                status_code = status.HTTP_401_UNAUTHORIZED,
                detail = "Invalid or expired token"
            )
        
        user_email = auth_user.user.email

        if not user_email:
            raise HTTPException(status_code = 401, detail = "No email found for user")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = f"Invalid authentication credentials: {e}",
            headers = {"WWW-Authenticate": "Bearer"}
        )

    db_user = crud.get_user_by_email(db, email = user_email)

    if db_user is None:
        db_user = crud.create_user(db, email=user_email)

    return db_user