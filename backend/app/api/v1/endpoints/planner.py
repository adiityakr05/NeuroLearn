from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.entities import User
from app.schemas.entities import (
    DailyStudyPlanResponse,
    StudySessionResponse,
    StudyPlanRescheduleRequest,
    StudyTaskStatusToggleRequest,
)
from app.services.planner_service import planner_service

router = APIRouter()


@router.get(
    "",
    response_model=DailyStudyPlanResponse,
    summary="Get daily study plan for a given date",
)
def get_daily_study_plan(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format (defaults to today UTC)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns the daily study schedule and task metrics for the authenticated student.
    Matches frontend studyService.getStudyPlan(date).
    """
    target_date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return planner_service.get_daily_study_plan(db, current_user.id, target_date)


@router.get(
    "/week",
    response_model=List[StudySessionResponse],
    summary="Get study sessions for the week",
)
def get_week_study_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns the list of upcoming study sessions for weekly agenda view.
    Matches frontend studyService.getWeekPlan().
    """
    return planner_service.get_week_study_plan(db, current_user.id)


@router.post(
    "/reschedule",
    summary="Reschedule a study task to a new date and time slot",
)
def reschedule_study_task(
    reschedule_in: StudyPlanRescheduleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Reschedules a study task with reason logging.
    Matches frontend studyService.rescheduleTask().
    """
    return planner_service.reschedule_task(db, current_user.id, reschedule_in)


@router.post(
    "/complete",
    summary="Mark study session as completed or toggle status",
)
def toggle_study_session_status(
    toggle_in: StudyTaskStatusToggleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Marks task status (completed, skipped, pending).
    Matches frontend studyService.toggleTaskStatus() and /study-session/complete route.
    """
    return planner_service.toggle_task_status(db, current_user.id, toggle_in)
