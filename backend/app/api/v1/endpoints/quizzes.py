from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.entities import User
from app.schemas.entities import QuizAttemptCreate, QuizAttemptResponse
from app.services.activity_service import activity_service

router = APIRouter()


@router.post(
    "",
    response_model=QuizAttemptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a quiz attempt",
)
def record_quiz_attempt(
    attempt_in: QuizAttemptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Records a quiz attempt for the current student.
    Validates total_questions, correct_answers, and score percentage bounds.
    """
    return activity_service.create_quiz_attempt(db, current_user.id, attempt_in)


@router.get(
    "",
    response_model=List[QuizAttemptResponse],
    summary="List quiz attempts with filters",
)
def list_quiz_attempts(
    subject_id: Optional[str] = Query(None, description="Filter by subject ID"),
    topic_id: Optional[str] = Query(None, description="Filter by topic ID"),
    start_date: Optional[str] = Query(None, description="Filter from ISO date"),
    end_date: Optional[str] = Query(None, description="Filter to ISO date"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lists quiz attempts for the student, with optional subject, topic, and date range filters.
    """
    return activity_service.get_quiz_attempts(
        db,
        user_id=current_user.id,
        subject_id=subject_id,
        topic_id=topic_id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{attempt_id}",
    response_model=QuizAttemptResponse,
    summary="Retrieve a quiz attempt by ID",
)
def get_quiz_attempt(
    attempt_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves a single quiz attempt by ID.
    Returns 404 if not found or unauthorized.
    """
    return activity_service.get_quiz_attempt_by_id(db, attempt_id, current_user.id)
