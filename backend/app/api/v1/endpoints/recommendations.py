from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.entities import User
from app.schemas.entities import (
    RecommendationResponse,
    RecommendationsHubResponse,
    RecommendationFeedbackRequest,
    RecommendationStatusUpdate,
)
from app.services.planner_service import recommendation_service

router = APIRouter()


@router.get(
    "",
    response_model=List[RecommendationResponse],
    summary="List student study recommendations",
)
def list_recommendations(
    status: Optional[str] = Query(None, description="Filter by status (pending, accepted, dismissed, completed)"),
    agent_element: Optional[str] = Query(None, description="Filter by agent element"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves all recommendations for the current student.
    """
    return recommendation_service.get_recommendations(
        db,
        user_id=current_user.id,
        status_filter=status,
        agent_element=agent_element,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/hub",
    response_model=RecommendationsHubResponse,
    summary="Get recommendations hub payload for frontend dashboard",
)
def get_recommendations_hub(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns active recommendations, history, counts by 4-elements, and total pending count.
    """
    return recommendation_service.get_recommendations_hub(db, current_user.id)


@router.get(
    "/{recommendation_id}",
    response_model=RecommendationResponse,
    summary="Retrieve recommendation details by ID",
)
def get_recommendation(
    recommendation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves details of a specific recommendation if owned by student.
    """
    return recommendation_service.get_recommendation_by_id(db, recommendation_id, current_user.id)


@router.post(
    "/{recommendation_id}/accept",
    response_model=RecommendationResponse,
    summary="Accept an AI recommendation and schedule study task",
)
def accept_recommendation(
    recommendation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Marks recommendation as accepted and automatically adds a study session to the student's schedule.
    Matches frontend studyService.acceptRecommendation(recId).
    """
    return recommendation_service.update_recommendation_status(
        db,
        recommendation_id,
        current_user.id,
        RecommendationStatusUpdate(status="accepted", student_adherence="Followed"),
    )


@router.post(
    "/{recommendation_id}/dismiss",
    response_model=RecommendationResponse,
    summary="Dismiss a recommendation",
)
def dismiss_recommendation(
    recommendation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Dismisses a recommendation.
    Matches frontend studyService.dismissRecommendation(recId).
    """
    return recommendation_service.update_recommendation_status(
        db,
        recommendation_id,
        current_user.id,
        RecommendationStatusUpdate(status="dismissed", student_adherence="Ignored"),
    )


@router.post(
    "/{recommendation_id}/feedback",
    response_model=RecommendationResponse,
    summary="Record student feedback on recommendation",
)
def record_recommendation_feedback(
    recommendation_id: str,
    feedback_in: RecommendationFeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Records student feedback (helpful: true/false, optional note).
    """
    return recommendation_service.record_feedback(
        db, recommendation_id, current_user.id, feedback_in
    )
