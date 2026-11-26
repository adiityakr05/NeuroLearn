from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.entities import User
from app.schemas.entities import (
    SubjectCreate,
    SubjectUpdate,
    SubjectResponse,
    SubjectWithTopicsResponse,
    TopicCreate,
    TopicUpdate,
    TopicResponse,
)
from app.services.curriculum_service import subject_service, topic_service

router = APIRouter()


@router.post(
    "",
    response_model=SubjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new academic subject",
)
def create_subject(
    subject_in: SubjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Creates a new academic subject for the currently authenticated student.
    Enforces uniqueness of subject code for the user.
    """
    return subject_service.create_subject(db, current_user.id, subject_in)


@router.get(
    "",
    response_model=List[SubjectWithTopicsResponse],
    summary="List subjects for the authenticated student",
)
def list_subjects(
    skip: int = Query(0, ge=0, description="Number of subjects to skip"),
    limit: int = Query(100, ge=1, le=100, description="Max subjects to return"),
    search: Optional[str] = Query(None, description="Search term for name or code"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves all subjects owned by the current student.
    Returns nested topics for direct frontend compatibility.
    """
    return subject_service.get_user_subjects(
        db, current_user.id, skip=skip, limit=limit, search=search
    )


@router.get(
    "/{subject_id}",
    response_model=SubjectWithTopicsResponse,
    summary="Get details of a single subject",
)
def get_subject(
    subject_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves a single subject by ID.
    Enforces strict ownership: returns 404 if not owned by authenticated student.
    """
    return subject_service.get_subject_by_id(db, subject_id, current_user.id)


@router.patch(
    "/{subject_id}",
    response_model=SubjectResponse,
    summary="Update an existing subject",
)
def update_subject(
    subject_id: str,
    subject_in: SubjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Updates mutable subject fields (name, code, color, description, target_mastery, exam_date).
    Validates code uniqueness if code is changed.
    """
    return subject_service.update_subject(db, subject_id, current_user.id, subject_in)


@router.put(
    "/{subject_id}",
    response_model=SubjectResponse,
    summary="Update an existing subject (PUT alias for frontend compatibility)",
    include_in_schema=False,
)
def update_subject_put(
    subject_id: str,
    subject_in: SubjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    PUT alias to support Axios client calls without breaking strict REST conventions.
    """
    return subject_service.update_subject(db, subject_id, current_user.id, subject_in)


@router.delete(
    "/{subject_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a subject",
)
def delete_subject(
    subject_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Deletes a subject and cascades deletion to child topics and study sessions.
    Returns 204 No Content upon success.
    """
    subject_service.delete_subject(db, subject_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ==============================================================================
# SUB-ROUTED TOPIC ENDPOINTS UNDER /api/subjects/{subject_id}/topics
# ==============================================================================

@router.post(
    "/{subject_id}/topics",
    response_model=TopicResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new topic under a subject",
)
def create_topic_under_subject(
    subject_id: str,
    topic_in: TopicCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Creates a topic under the specified subject.
    Verifies that the current student owns the subject.
    """
    return topic_service.create_topic(db, subject_id, current_user.id, topic_in)


@router.get(
    "/{subject_id}/topics",
    response_model=List[TopicResponse],
    summary="List topics for a subject",
)
def list_topics_under_subject(
    subject_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves all topics under an owned subject.
    Supports pagination and optional name search.
    """
    return topic_service.get_subject_topics(
        db, subject_id, current_user.id, skip=skip, limit=limit, search=search
    )


@router.put(
    "/{subject_id}/topics/{topic_id}",
    response_model=TopicResponse,
    summary="Update topic (PUT alias matching frontend client)",
    include_in_schema=False,
)
def update_topic_nested_put(
    subject_id: str,
    topic_id: str,
    topic_in: TopicUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return topic_service.update_topic(db, topic_id, current_user.id, topic_in)


@router.delete(
    "/{subject_id}/topics/{topic_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete topic (nested route matching frontend client)",
    include_in_schema=False,
)
def delete_topic_nested(
    subject_id: str,
    topic_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    topic_service.delete_topic(db, topic_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
