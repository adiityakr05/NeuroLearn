from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.entities import User
from app.schemas.entities import SpacedRepetitionItemResponse
from app.services.planner_service import planner_service

router = APIRouter()


@router.get(
    "",
    response_model=List[SpacedRepetitionItemResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Spaced Repetition Review Queue",
    description="Calculates and returns the prioritized Ebbinghaus spaced repetition review queue for the authenticated student.",
)
def get_spaced_repetition_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns the student's topics prioritized by forgetting risk and revision urgency.
    Matches frontend studyService.getSpacedRepetitions().
    """
    return planner_service.get_spaced_repetition_queue(db, current_user.id)
