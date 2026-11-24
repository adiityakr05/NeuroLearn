from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.entities import User
from app.schemas.entities import OverallProgressStats
from app.services.activity_service import activity_service

router = APIRouter()


@router.get(
    "",
    response_model=OverallProgressStats,
    summary="Get overall study statistics and progress metrics",
)
@router.get(
    "/progress",
    response_model=OverallProgressStats,
    summary="Get overall study statistics and progress metrics",
)
def get_progress_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Computes real-time progress metrics from database records:
    - Total study time (minutes and hours)
    - Total and completed study sessions
    - Subject-wise progress (mastery, topics count, sessions)
    - Topic-wise progress (retention, revisions count, quiz count)
    - Quiz accuracy averages
    - Overall progress percentage
    """
    return activity_service.get_overall_progress(db, current_user.id)
