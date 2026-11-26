from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.entities import User
from app.schemas.entities import TopicUpdate, TopicResponse
from app.services.curriculum_service import topic_service

router = APIRouter()


@router.get(
    "/{topic_id}",
    response_model=TopicResponse,
    summary="Get details of a single topic",
)
def get_topic(
    topic_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves a topic by ID.
    Enforces that the parent subject is owned by the authenticated student.
    Returns 404 if not found or unauthorized.
    """
    return topic_service.get_topic_by_id(db, topic_id, current_user.id)


@router.patch(
    "/{topic_id}",
    response_model=TopicResponse,
    summary="Update an existing topic",
)
def update_topic(
    topic_id: str,
    topic_in: TopicUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Updates mutable topic attributes (name, difficulty, mastery_score, retention_score, completed, revision dates).
    Validates name uniqueness within its parent subject.
    """
    return topic_service.update_topic(db, topic_id, current_user.id, topic_in)


@router.delete(
    "/{topic_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a topic",
)
def delete_topic(
    topic_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Deletes a topic after verifying parent subject ownership.
    Returns 204 No Content.
    """
    topic_service.delete_topic(db, topic_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
