from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.entities import User
from app.schemas.entities import OverallProgressStats, HistoricalAnalyticsResponse
from app.services.activity_service import activity_service
from app.services.analytics_service import analytics_service

router = APIRouter()


@router.get(
    "/history",
    response_model=HistoricalAnalyticsResponse,
    summary="Get longitudinal historical analytics and reconstructed trajectories",
)
def get_historical_analytics(
    timeRange: Optional[str] = Query("30d", description="Window filter: '14d', '30d', 'semester', or '7d'"),
    window_days: Optional[int] = Query(None, description="Optional integer day override (7, 14, 30, 120)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns verifiable historical analytics for the authenticated student:
    - Chronologically reconstructed topic mastery trajectories from quiz attempts (including pre-window history).
    - Retention analytics: current decay parameters, predicted curves, and discrete observed recall events.
    - Study behavior: planned vs measured actual duration, legacy estimates, and completed vs abandoned sessions.
    - Recommendation lifecycle effectiveness with mutually exclusive status partitions and non-causal performance correlation.
    - Pre-formatted frontend_bundle adapting to Recharts components in Analytics.jsx.
    """
    effective_range = f"{window_days}d" if window_days else (timeRange or "30d")
    return analytics_service.get_historical_analytics(db, current_user.id, time_range=effective_range)


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

