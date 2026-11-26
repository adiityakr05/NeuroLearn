from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.entities import User
from app.schemas.entities import RevisionHistoryCreate, RevisionHistoryResponse
from app.services.activity_service import activity_service

router = APIRouter()


@router.post(
    "",
    response_model=RevisionHistoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a topic revision",
)
def record_revision(
    rev_in: RevisionHistoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Records a topic revision history log for the current student.
    Validates score bounds between 0.0 and 100.0.
    """
    return activity_service.create_revision_record(db, current_user.id, rev_in)


@router.get(
    "",
    response_model=List[RevisionHistoryResponse],
    summary="List revision history records",
)
def list_revision_history(
    topic_id: Optional[str] = Query(None, description="Filter by topic ID"),
    start_date: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lists topic revision records belonging to the student.
    """
    return activity_service.get_revision_history(
        db,
        user_id=current_user.id,
        topic_id=topic_id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{revision_id}",
    response_model=RevisionHistoryResponse,
    summary="Retrieve a revision record by ID",
)
def get_revision(
    revision_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves a single revision history record by ID.
    Returns 404 if not found or unauthorized.
    """
    return activity_service.get_revision_by_id(db, revision_id, current_user.id)
