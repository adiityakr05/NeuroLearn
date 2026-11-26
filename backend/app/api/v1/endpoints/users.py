from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.entities import User
from app.schemas.entities import UserResponse, UserUpdate
from app.services.user_service import user_service

router = APIRouter()


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
def get_user_profile(current_user: User = Depends(get_current_user)):
    """
    Returns the profile of the student currently authenticated via JWT.
    """
    return current_user


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
)
def update_user_profile(
    update_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Allows safe profile updates (e.g. full_name, program, semester, avatar_url).
    Prevents modification of protected fields (id, email, password_hash, is_active).
    """
    updated_user = user_service.update_profile(db, current_user, update_in)
    return updated_user
