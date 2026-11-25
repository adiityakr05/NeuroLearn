"""
Student Context Builder
=======================
Gathers and synthesizes student context from existing SQLAlchemy models and database queries.
Safely handles missing or incomplete records without fabricating data.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.entities import (
    User,
    Subject,
    Topic,
    QuizAttempt,
    StudySession,
    Recommendation,
)
from app.ml.feature_extractor import parse_datetime, FeatureExtractor
from app.agents.schemas import (
    StudentContext,
    StudentProfileContext,
    SubjectContext,
    TopicContext,
    QuizAttemptContext,
    StudySessionContext,
    ExistingRecommendationContext,
)


class StudentContextBuilder:
    """
    Constructs a comprehensive, immutable-friendly StudentContext snapshot
    from the database for agent evaluation.
    """

    @staticmethod
    def build_from_db(
        db: Session,
        user_id: str,
        reference_time: Optional[datetime] = None,
        daily_capacity_minutes: int = 120,
    ) -> Optional[StudentContext]:
        """
        Queries existing database entities and constructs the unified StudentContext.
        Enforces tenant isolation by scoping all queries to user_id.
        """
        ref_dt = reference_time or datetime.now(timezone.utc)
        if ref_dt.tzinfo is None:
            ref_dt = ref_dt.replace(tzinfo=timezone.utc)

        user = db.scalar(select(User).where(User.id == user_id))
        if not user:
            return None

        # Build Student Profile
        student_profile = StudentProfileContext(
            user_id=user.id,
            full_name=user.full_name or "Student",
            email=user.email,
            program=user.program,
            semester=user.semester,
            daily_capacity_minutes=daily_capacity_minutes,
        )

        # 1. Fetch Subjects
        subjects_orm = list(
            db.scalars(
                select(Subject).where(Subject.user_id == user_id).order_by(Subject.created_at.asc())
            ).all()
        )
        subject_map: Dict[str, Subject] = {s.id: s for s in subjects_orm}

        subject_contexts: List[SubjectContext] = []
        for s in subjects_orm:
            days_to_exam: Optional[float] = None
            if s.exam_date:
                exam_dt = parse_datetime(s.exam_date)
                if exam_dt:
                    days_to_exam = max(0.0, (exam_dt - ref_dt).total_seconds() / 86400.0)

            subject_contexts.append(
                SubjectContext(
                    id=s.id,
                    name=s.name,
                    code=s.code,
                    target_mastery=float(s.target_mastery or 80.0),
                    exam_date=s.exam_date,
                    days_until_exam=days_to_exam,
                    topics_count=len(s.topics) if hasattr(s, "topics") and s.topics else 0,
                )
            )

        # 2. Fetch Topics belonging to student's subjects
        subject_ids = list(subject_map.keys())
        topics_orm: List[Topic] = []
        if subject_ids:
            topics_orm = list(
                db.scalars(
                    select(Topic)
                    .where(Topic.subject_id.in_(subject_ids))
                    .order_by(Topic.created_at.asc())
                ).all()
            )

        topic_contexts: List[TopicContext] = []
        for t in topics_orm:
            subj = subject_map.get(t.subject_id)
            subj_name = subj.name if subj else "Unknown Subject"
            exam_dt = parse_datetime(subj.exam_date) if subj and subj.exam_date else None
            days_to_exam = (
                max(0.0, (exam_dt - ref_dt).total_seconds() / 86400.0) if exam_dt else None
            )
            elapsed_days = FeatureExtractor.extract_elapsed_days(t.last_revised, ref_dt)

            topic_contexts.append(
                TopicContext(
                    id=t.id,
                    subject_id=t.subject_id,
                    subject_name=subj_name,
                    name=t.name,
                    difficulty=t.difficulty or "Medium",
                    mastery_score=float(t.mastery_score if t.mastery_score is not None else 50.0),
                    retention_score=float(t.retention_score if t.retention_score is not None else 70.0),
                    decay_rate_lambda=float(t.decay_rate_lambda if t.decay_rate_lambda is not None else 0.08),
                    completed=bool(t.completed),
                    last_revised=t.last_revised,
                    next_revision=t.next_revision,
                    elapsed_days=elapsed_days,
                    exam_date=exam_dt,
                    days_until_exam=days_to_exam,
                )
            )

        # 3. Fetch Recent Quiz Attempts (last 30)
        quizzes_orm = list(
            db.scalars(
                select(QuizAttempt)
                .where(QuizAttempt.user_id == user_id)
                .order_by(QuizAttempt.attempted_at.desc())
                .limit(30)
            ).all()
        )
        topic_name_map = {t.id: t.name for t in topics_orm}
        quiz_contexts = [
            QuizAttemptContext(
                id=q.id,
                topic_id=q.topic_id,
                topic_name=topic_name_map.get(q.topic_id, "Unknown Topic"),
                score=float(q.score),
                accuracy=float(q.accuracy),
                total_questions=q.total_questions,
                correct_answers=q.correct_answers,
                attempted_at=q.attempted_at,
                critic_evaluated=bool(q.critic_evaluated),
                critic_notes=q.critic_notes,
            )
            for q in quizzes_orm
        ]

        # 4. Fetch Active/Pending Study Sessions
        sessions_orm = list(
            db.scalars(
                select(StudySession)
                .where(StudySession.user_id == user_id)
                .order_by(StudySession.date.desc())
                .limit(50)
            ).all()
        )
        session_contexts = [
            StudySessionContext(
                id=sess.id,
                subject_id=sess.subject_id,
                topic_id=sess.topic_id,
                date=sess.date,
                duration_minutes=sess.duration_minutes,
                status=sess.status,
                priority=sess.priority,
            )
            for sess in sessions_orm
        ]

        # 5. Fetch Pending Recommendations
        recs_orm = list(
            db.scalars(
                select(Recommendation)
                .where(Recommendation.user_id == user_id, Recommendation.status == "pending")
                .limit(50)
            ).all()
        )
        rec_contexts = [
            ExistingRecommendationContext(
                id=r.id,
                subject_id=r.subject_id,
                topic_id=r.topic_id,
                agent_element=r.agent_element,
                type=r.type,
                priority=r.priority,
                status=r.status,
                title=r.title,
            )
            for r in recs_orm
        ]

        return StudentContext(
            student=student_profile,
            subjects=subject_contexts,
            topics=topic_contexts,
            recent_quizzes=quiz_contexts,
            study_sessions=session_contexts,
            active_recommendations=rec_contexts,
            reference_time=ref_dt,
        )


student_context_builder = StudentContextBuilder()
