from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.entities import User
from app.schemas.entities import (
    StudySessionCreate,
    StudySessionUpdate,
    StudySessionResponse,
)
from app.services.activity_service import activity_service

router = APIRouter()


@router.post(
    "",
    response_model=StudySessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new study session",
)
def create_study_session(
    session_in: StudySessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Creates a new study session for the current student.
    Validates that the referenced subject and optional topic belong to the authenticated user.
    """
    return activity_service.create_study_session(db, current_user.id, session_in)


@router.get(
    "",
    response_model=List[StudySessionResponse],
    summary="List current user's study sessions with filters",
)
def list_study_sessions(
    subject_id: Optional[str] = Query(None, description="Filter by subject ID"),
    topic_id: Optional[str] = Query(None, description="Filter by topic ID"),
    start_date: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Filter by status (pending, completed)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lists the current user's study sessions with optional subject, topic, and date range filters.
    """
    return activity_service.get_study_sessions(
        db,
        user_id=current_user.id,
        subject_id=subject_id,
        topic_id=topic_id,
        start_date=start_date,
        end_date=end_date,
        status_filter=status,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{session_id}",
    response_model=StudySessionResponse,
    summary="Retrieve a study session by ID",
)
def get_study_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves a study session if owned by the current student.
    Returns 404 if not found or unauthorized.
    """
    return activity_service.get_study_session_by_id(db, session_id, current_user.id)


@router.patch(
    "/{session_id}",
    response_model=StudySessionResponse,
    summary="Update a study session",
)
def update_study_session(
    session_id: str,
    session_in: StudySessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Updates mutable study session fields (status, duration, notes/title, date, slot).
    """
    return activity_service.update_study_session(db, session_id, current_user.id, session_in)


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a study session",
)
def delete_study_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Deletes a study session belonging to the current student.
    Returns 204 No Content.
    """
    activity_service.delete_study_session(db, session_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
