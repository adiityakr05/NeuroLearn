from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from fastapi import HTTPException, status

from app.models.entities import Subject, Topic
from app.schemas.entities import (
    SubjectCreate,
    SubjectUpdate,
    TopicCreate,
    TopicUpdate,
)


class SubjectService:
    @staticmethod
    def get_user_subjects(
        db: Session,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
    ) -> List[Subject]:
        """
        Lists all subjects owned by the authenticated student.
        Supports pagination (skip, limit) and optional search across name and code.
        """
        query = select(Subject).where(Subject.user_id == user_id)
        if search:
            search_term = f"%{search.strip()}%"
            query = query.where(
                (Subject.name.ilike(search_term)) | (Subject.code.ilike(search_term))
            )
        query = query.order_by(Subject.created_at.desc()).offset(skip).limit(limit)
        return list(db.scalars(query).all())

    @staticmethod
    def get_subject_by_id(db: Session, subject_id: str, user_id: str) -> Subject:
        """
        Retrieves a single subject if and only if owned by the authenticated student.
        Raises HTTP 404 if not found or belongs to another student.
        """
        subject = db.scalar(
            select(Subject).where(Subject.id == subject_id, Subject.user_id == user_id)
        )
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subject not found",
            )
        return subject

    @staticmethod
    def create_subject(db: Session, user_id: str, subject_in: SubjectCreate) -> Subject:
        """
        Creates a new subject for the authenticated student.
        Validates duplicate subject code for the same user.
        """
        existing = db.scalar(
            select(Subject).where(
                Subject.user_id == user_id,
                Subject.code == subject_in.code.strip(),
            )
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Subject with code '{subject_in.code}' already exists in your curriculum",
            )

        new_subject = Subject(
            user_id=user_id,
            name=subject_in.name.strip(),
            code=subject_in.code.strip(),
            color=subject_in.color or "#6366F1",
            description=subject_in.description,
            target_mastery=subject_in.target_mastery if subject_in.target_mastery is not None else 80.0,
            exam_date=subject_in.exam_date,
        )
        db.add(new_subject)
        db.commit()
        db.refresh(new_subject)
        return new_subject

    @staticmethod
    def update_subject(
        db: Session,
        subject_id: str,
        user_id: str,
        subject_in: SubjectUpdate,
    ) -> Subject:
        """
        Updates permitted subject fields for an owned subject.
        """
        subject = SubjectService.get_subject_by_id(db, subject_id, user_id)
        update_data = subject_in.model_dump(exclude_unset=True)

        # Check code uniqueness if code is being updated
        if "code" in update_data and update_data["code"] is not None:
            new_code = update_data["code"].strip()
            if new_code != subject.code:
                existing = db.scalar(
                    select(Subject).where(
                        Subject.user_id == user_id,
                        Subject.code == new_code,
                        Subject.id != subject.id,
                    )
                )
                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Subject with code '{new_code}' already exists in your curriculum",
                    )
                update_data["code"] = new_code

        if "name" in update_data and update_data["name"] is not None:
            update_data["name"] = update_data["name"].strip()

        for field, value in update_data.items():
            setattr(subject, field, value)

        db.commit()
        db.refresh(subject)
        return subject

    @staticmethod
    def delete_subject(db: Session, subject_id: str, user_id: str) -> None:
        """
        Deletes a subject owned by the authenticated student.
        Cascade rules configured on models delete associated topics, study sessions, etc.
        """
        subject = SubjectService.get_subject_by_id(db, subject_id, user_id)
        db.delete(subject)
        db.commit()


class TopicService:
    @staticmethod
    def get_subject_topics(
        db: Session,
        subject_id: str,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
    ) -> List[Topic]:
        """
        Lists topics under an owned subject.
        Verifies student owns the parent subject.
        """
        # Ownership check
        SubjectService.get_subject_by_id(db, subject_id, user_id)

        query = select(Topic).where(Topic.subject_id == subject_id)
        if search:
            search_term = f"%{search.strip()}%"
            query = query.where(Topic.name.ilike(search_term))
        query = query.order_by(Topic.created_at.asc()).offset(skip).limit(limit)
        return list(db.scalars(query).all())

    @staticmethod
    def get_topic_by_id(db: Session, topic_id: str, user_id: str) -> Topic:
        """
        Retrieves a single topic and verifies that its parent subject belongs to the user.
        Raises 404 if topic doesn't exist or parent subject does not belong to the user.
        """
        topic = db.scalar(
            select(Topic)
            .join(Subject, Topic.subject_id == Subject.id)
            .where(Topic.id == topic_id, Subject.user_id == user_id)
        )
        if not topic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Topic not found",
            )
        return topic

    @staticmethod
    def create_topic(
        db: Session,
        subject_id: str,
        user_id: str,
        topic_in: TopicCreate,
    ) -> Topic:
        """
        Creates a new topic under an owned subject.
        Verifies ownership and validates topic name uniqueness within the subject.
        """
        SubjectService.get_subject_by_id(db, subject_id, user_id)

        # Validate difficulty
        difficulty = (topic_in.difficulty or "Medium").capitalize()
        if difficulty not in ("Easy", "Medium", "Hard"):
            difficulty = "Medium"

        # Check duplicate name within subject
        topic_name = topic_in.name.strip()
        existing = db.scalar(
            select(Topic).where(
                Topic.subject_id == subject_id,
                Topic.name == topic_name,
            )
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Topic '{topic_name}' already exists in this subject",
            )

        new_topic = Topic(
            subject_id=subject_id,
            name=topic_name,
            difficulty=difficulty,
            mastery_score=topic_in.mastery_score if topic_in.mastery_score is not None else 50.0,
            retention_score=topic_in.retention_score if topic_in.retention_score is not None else 70.0,
            completed=topic_in.completed if topic_in.completed is not None else False,
            last_revised=topic_in.last_revised,
            next_revision=topic_in.next_revision,
        )
        db.add(new_topic)
        db.commit()
        db.refresh(new_topic)
        return new_topic

    @staticmethod
    def update_topic(
        db: Session,
        topic_id: str,
        user_id: str,
        topic_in: TopicUpdate,
    ) -> Topic:
        """
        Updates permitted fields on an owned topic.
        """
        topic = TopicService.get_topic_by_id(db, topic_id, user_id)
        update_data = topic_in.model_dump(exclude_unset=True)

        if "name" in update_data and update_data["name"] is not None:
            new_name = update_data["name"].strip()
            if new_name != topic.name:
                existing = db.scalar(
                    select(Topic).where(
                        Topic.subject_id == topic.subject_id,
                        Topic.name == new_name,
                        Topic.id != topic.id,
                    )
                )
                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Topic '{new_name}' already exists in this subject",
                    )
                update_data["name"] = new_name

        if "difficulty" in update_data and update_data["difficulty"] is not None:
            diff = update_data["difficulty"].capitalize()
            if diff in ("Easy", "Medium", "Hard"):
                update_data["difficulty"] = diff

        for field, value in update_data.items():
            setattr(topic, field, value)

        db.commit()
        db.refresh(topic)
        return topic

    @staticmethod
    def delete_topic(db: Session, topic_id: str, user_id: str) -> None:
        """
        Deletes a topic after verifying parent subject ownership.
        """
        topic = TopicService.get_topic_by_id(db, topic_id, user_id)
        db.delete(topic)
        db.commit()


subject_service = SubjectService()
topic_service = TopicService()
