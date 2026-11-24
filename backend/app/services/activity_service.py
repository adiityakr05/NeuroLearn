from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_

from app.models.entities import (
    User,
    Subject,
    Topic,
    StudySession,
    QuizAttempt,
    RevisionHistory,
)
from app.schemas.entities import (
    StudySessionCreate,
    StudySessionUpdate,
    QuizAttemptCreate,
    RevisionHistoryCreate,
    SubjectProgress,
    TopicProgress,
    OverallProgressStats,
)


class ActivityService:
    # ==========================================================================
    # 1. STUDY SESSIONS
    # ==========================================================================
    @staticmethod
    def get_study_sessions(
        db: Session,
        user_id: str,
        subject_id: Optional[str] = None,
        topic_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        status_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        query = select(StudySession).where(StudySession.user_id == user_id)
        if subject_id:
            query = query.where(StudySession.subject_id == subject_id)
        if topic_id:
            query = query.where(StudySession.topic_id == topic_id)
        if start_date:
            query = query.where(StudySession.date >= start_date)
        if end_date:
            query = query.where(StudySession.date <= end_date)
        if status_filter:
            query = query.where(StudySession.status == status_filter)

        query = query.order_by(StudySession.date.desc(), StudySession.created_at.desc()).offset(skip).limit(limit)
        sessions = list(db.scalars(query).all())

        return [
            {
                "id": s.id,
                "user_id": s.user_id,
                "subject_id": s.subject_id,
                "topic_id": s.topic_id,
                "title": s.ai_reason or "Study Session",
                "date": s.date,
                "session_date": s.date,
                "time_slot": s.time_slot,
                "duration_minutes": s.duration_minutes,
                "status": s.status,
                "priority": s.priority,
                "retention_score": s.retention_score,
                "repetition_cycle": s.repetition_cycle,
                "is_overdue": s.is_overdue,
                "ai_reason": s.ai_reason,
                "notes": s.ai_reason,
                "completed_at": s.completed_at,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
            }
            for s in sessions
        ]

    @staticmethod
    def get_study_session_by_id(db: Session, session_id: str, user_id: str) -> Dict[str, Any]:
        session = db.scalar(
            select(StudySession).where(StudySession.id == session_id, StudySession.user_id == user_id)
        )
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Study session not found",
            )
        return {
            "id": session.id,
            "user_id": session.user_id,
            "subject_id": session.subject_id,
            "topic_id": session.topic_id,
            "title": session.ai_reason or "Study Session",
            "date": session.date,
            "session_date": session.date,
            "time_slot": session.time_slot,
            "duration_minutes": session.duration_minutes,
            "status": session.status,
            "priority": session.priority,
            "retention_score": session.retention_score,
            "repetition_cycle": session.repetition_cycle,
            "is_overdue": session.is_overdue,
            "ai_reason": session.ai_reason,
            "notes": session.ai_reason,
            "completed_at": session.completed_at,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
        }

    @staticmethod
    def create_study_session(
        db: Session,
        user_id: str,
        session_in: StudySessionCreate,
    ) -> Dict[str, Any]:
        # Validate that subject belongs to user
        subject = db.scalar(
            select(Subject).where(Subject.id == session_in.subject_id, Subject.user_id == user_id)
        )
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subject not found or does not belong to user",
            )

        # Validate topic if supplied
        if session_in.topic_id:
            topic = db.scalar(
                select(Topic)
                .join(Subject, Topic.subject_id == Subject.id)
                .where(Topic.id == session_in.topic_id, Subject.user_id == user_id)
            )
            if not topic:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Topic not found or does not belong to user",
                )

        target_date = session_in.session_date or session_in.date
        reason_text = session_in.notes or session_in.title or session_in.ai_reason

        new_session = StudySession(
            user_id=user_id,
            subject_id=session_in.subject_id,
            topic_id=session_in.topic_id,
            date=target_date,
            time_slot=session_in.time_slot,
            duration_minutes=session_in.duration_minutes,
            status=session_in.status or "pending",
            priority=session_in.priority or "medium",
            retention_score=session_in.retention_score,
            repetition_cycle=session_in.repetition_cycle,
            is_overdue=session_in.is_overdue,
            ai_reason=reason_text,
        )
        if new_session.status == "completed":
            new_session.completed_at = datetime.now(timezone.utc)

        db.add(new_session)
        db.commit()
        db.refresh(new_session)

        return ActivityService.get_study_session_by_id(db, new_session.id, user_id)

    @staticmethod
    def update_study_session(
        db: Session,
        session_id: str,
        user_id: str,
        session_in: StudySessionUpdate,
    ) -> Dict[str, Any]:
        session = db.scalar(
            select(StudySession).where(StudySession.id == session_id, StudySession.user_id == user_id)
        )
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Study session not found",
            )

        update_dict = session_in.model_dump(exclude_unset=True)
        if "session_date" in update_dict and update_dict["session_date"]:
            session.date = update_dict["session_date"]
        elif "date" in update_dict and update_dict["date"]:
            session.date = update_dict["date"]

        if "notes" in update_dict and update_dict["notes"]:
            session.ai_reason = update_dict["notes"]
        elif "title" in update_dict and update_dict["title"]:
            session.ai_reason = update_dict["title"]

        if "status" in update_dict and update_dict["status"]:
            session.status = update_dict["status"]
            if session.status == "completed" and not session.completed_at:
                session.completed_at = datetime.now(timezone.utc)

        for field in ["time_slot", "duration_minutes", "priority"]:
            if field in update_dict and update_dict[field] is not None:
                setattr(session, field, update_dict[field])

        db.commit()
        db.refresh(session)
        return ActivityService.get_study_session_by_id(db, session.id, user_id)

    @staticmethod
    def delete_study_session(db: Session, session_id: str, user_id: str) -> None:
        session = db.scalar(
            select(StudySession).where(StudySession.id == session_id, StudySession.user_id == user_id)
        )
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Study session not found",
            )
        db.delete(session)
        db.commit()

    # ==========================================================================
    # 2. QUIZ ATTEMPTS
    # ==========================================================================
    @staticmethod
    def get_quiz_attempts(
        db: Session,
        user_id: str,
        subject_id: Optional[str] = None,
        topic_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        query = select(QuizAttempt).where(QuizAttempt.user_id == user_id)
        if topic_id:
            query = query.where(QuizAttempt.topic_id == topic_id)
        if subject_id:
            query = query.join(Topic, QuizAttempt.topic_id == Topic.id).where(Topic.subject_id == subject_id)
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
                query = query.where(QuizAttempt.attempted_at >= start_dt)
            except Exception:
                pass
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
                query = query.where(QuizAttempt.attempted_at <= end_dt)
            except Exception:
                pass

        query = query.order_by(QuizAttempt.attempted_at.desc()).offset(skip).limit(limit)
        attempts = list(db.scalars(query).all())

        results = []
        for a in attempts:
            parent_topic = db.scalar(select(Topic).where(Topic.id == a.topic_id))
            sub_id = parent_topic.subject_id if parent_topic else None
            results.append(
                {
                    "id": a.id,
                    "user_id": a.user_id,
                    "topic_id": a.topic_id,
                    "subject_id": sub_id,
                    "title": a.title,
                    "score": a.score,
                    "accuracy": a.accuracy,
                    "score_percentage": a.accuracy,
                    "total_questions": a.total_questions,
                    "correct_answers": a.correct_answers,
                    "time_taken_seconds": None,
                    "attempted_at": a.attempted_at,
                    "critic_evaluated": a.critic_evaluated,
                    "critic_notes": a.critic_notes,
                    "created_at": a.attempted_at,
                }
            )
        return results

    @staticmethod
    def get_quiz_attempt_by_id(db: Session, attempt_id: str, user_id: str) -> Dict[str, Any]:
        a = db.scalar(
            select(QuizAttempt).where(QuizAttempt.id == attempt_id, QuizAttempt.user_id == user_id)
        )
        if not a:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz attempt not found",
            )
        parent_topic = db.scalar(select(Topic).where(Topic.id == a.topic_id))
        sub_id = parent_topic.subject_id if parent_topic else None
        return {
            "id": a.id,
            "user_id": a.user_id,
            "topic_id": a.topic_id,
            "subject_id": sub_id,
            "title": a.title,
            "score": a.score,
            "accuracy": a.accuracy,
            "score_percentage": a.accuracy,
            "total_questions": a.total_questions,
            "correct_answers": a.correct_answers,
            "time_taken_seconds": None,
            "attempted_at": a.attempted_at,
            "critic_evaluated": a.critic_evaluated,
            "critic_notes": a.critic_notes,
            "created_at": a.attempted_at,
        }

    @staticmethod
    def create_quiz_attempt(
        db: Session,
        user_id: str,
        attempt_in: QuizAttemptCreate,
    ) -> Dict[str, Any]:
        # Validate that topic belongs to an owned subject
        topic = db.scalar(
            select(Topic)
            .join(Subject, Topic.subject_id == Subject.id)
            .where(Topic.id == attempt_in.topic_id, Subject.user_id == user_id)
        )
        if not topic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Topic not found or does not belong to user",
            )

        # Validate questions & correct answers
        if attempt_in.total_questions <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="total_questions must be greater than zero",
            )
        if attempt_in.correct_answers < 0 or attempt_in.correct_answers > attempt_in.total_questions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="correct_answers must be between 0 and total_questions",
            )

        # Calculate / validate score percentage
        calculated_accuracy = round((attempt_in.correct_answers / attempt_in.total_questions) * 100.0, 2)
        score_val = (
            attempt_in.score_percentage
            if attempt_in.score_percentage is not None
            else attempt_in.score
            if attempt_in.score is not None
            else calculated_accuracy
        )
        if score_val < 0.0 or score_val > 100.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="score_percentage must be between 0 and 100",
            )

        new_attempt = QuizAttempt(
            user_id=user_id,
            topic_id=attempt_in.topic_id,
            title=attempt_in.title or f"{topic.name} Quiz",
            score=score_val,
            accuracy=calculated_accuracy,
            total_questions=attempt_in.total_questions,
            correct_answers=attempt_in.correct_answers,
            attempted_at=attempt_in.attempted_at or datetime.now(timezone.utc),
            critic_evaluated=False,
            critic_notes=attempt_in.critic_notes,
        )
        db.add(new_attempt)

        # Automatically update topic mastery based on latest quiz score
        topic.mastery_score = round((topic.mastery_score * 0.7) + (score_val * 0.3), 1)
        topic.last_revised = datetime.now(timezone.utc)

        db.commit()
        db.refresh(new_attempt)
        return ActivityService.get_quiz_attempt_by_id(db, new_attempt.id, user_id)

    # ==========================================================================
    # 3. REVISION HISTORY
    # ==========================================================================
    @staticmethod
    def get_revision_history(
        db: Session,
        user_id: str,
        topic_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        query = (
            select(RevisionHistory)
            .join(Topic, RevisionHistory.topic_id == Topic.id)
            .join(Subject, Topic.subject_id == Subject.id)
            .where(Subject.user_id == user_id)
        )
        if topic_id:
            query = query.where(RevisionHistory.topic_id == topic_id)
        if start_date:
            query = query.where(RevisionHistory.revision_date >= start_date)
        if end_date:
            query = query.where(RevisionHistory.revision_date <= end_date)

        query = query.order_by(RevisionHistory.revision_date.desc(), RevisionHistory.created_at.desc()).offset(skip).limit(limit)
        revisions = list(db.scalars(query).all())

        return [
            {
                "id": r.id,
                "user_id": user_id,
                "topic_id": r.topic_id,
                "revision_date": r.revision_date,
                "score": r.score,
                "mastery_score": r.score,
                "retention_score": r.score,
                "interval_days": r.interval_days,
                "repetition_number": r.repetition_number,
                "notes": r.note,
                "created_at": r.created_at,
            }
            for r in revisions
        ]

    @staticmethod
    def get_revision_by_id(db: Session, revision_id: str, user_id: str) -> Dict[str, Any]:
        r = db.scalar(
            select(RevisionHistory)
            .join(Topic, RevisionHistory.topic_id == Topic.id)
            .join(Subject, Topic.subject_id == Subject.id)
            .where(RevisionHistory.id == revision_id, Subject.user_id == user_id)
        )
        if not r:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Revision record not found",
            )
        return {
            "id": r.id,
            "user_id": user_id,
            "topic_id": r.topic_id,
            "revision_date": r.revision_date,
            "score": r.score,
            "mastery_score": r.score,
            "retention_score": r.score,
            "interval_days": r.interval_days,
            "repetition_number": r.repetition_number,
            "notes": r.note,
            "created_at": r.created_at,
        }

    @staticmethod
    def create_revision_record(
        db: Session,
        user_id: str,
        rev_in: RevisionHistoryCreate,
    ) -> Dict[str, Any]:
        # Validate that topic belongs to owned subject
        topic = db.scalar(
            select(Topic)
            .join(Subject, Topic.subject_id == Subject.id)
            .where(Topic.id == rev_in.topic_id, Subject.user_id == user_id)
        )
        if not topic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Topic not found or does not belong to user",
            )

        # Validate score 0 to 100
        score_val = (
            rev_in.score
            if rev_in.score is not None
            else rev_in.mastery_score
            if rev_in.mastery_score is not None
            else 50.0
        )
        if score_val < 0.0 or score_val > 100.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="score must be between 0.0 and 100.0",
            )

        new_rev = RevisionHistory(
            topic_id=rev_in.topic_id,
            revision_date=rev_in.revision_date,
            score=score_val,
            interval_days=rev_in.interval_days,
            repetition_number=rev_in.repetition_number,
            note=rev_in.notes,
        )
        db.add(new_rev)

        # Update topic metrics
        if rev_in.mastery_score is not None:
            topic.mastery_score = rev_in.mastery_score
        if rev_in.retention_score is not None:
            topic.retention_score = rev_in.retention_score
        topic.last_revised = datetime.now(timezone.utc)

        db.commit()
        db.refresh(new_rev)
        return ActivityService.get_revision_by_id(db, new_rev.id, user_id)

    # ==========================================================================
    # 4. PROGRESS TRACKING & AGGREGATE METRICS
    # ==========================================================================
    @staticmethod
    def get_overall_progress(db: Session, user_id: str) -> OverallProgressStats:
        # All subjects
        subjects = list(db.scalars(select(Subject).where(Subject.user_id == user_id)).all())
        subject_ids = [s.id for s in subjects]

        # All topics
        topics = (
            list(db.scalars(select(Topic).where(Topic.subject_id.in_(subject_ids))).all())
            if subject_ids
            else []
        )
        topic_ids = [t.id for t in topics]

        # Study sessions
        sessions = list(db.scalars(select(StudySession).where(StudySession.user_id == user_id)).all())
        completed_sessions = [s for s in sessions if s.status == "completed"]
        total_study_minutes = sum(s.duration_minutes for s in completed_sessions)

        # Quiz attempts
        quizzes = list(db.scalars(select(QuizAttempt).where(QuizAttempt.user_id == user_id)).all())
        avg_quiz_accuracy = (
            round(sum(q.accuracy for q in quizzes) / len(quizzes), 1) if quizzes else 0.0
        )

        # Revisions
        revisions_count = (
            db.scalar(
                select(func.count(RevisionHistory.id))
                .join(Topic, RevisionHistory.topic_id == Topic.id)
                .join(Subject, Topic.subject_id == Subject.id)
                .where(Subject.user_id == user_id)
            )
            or 0
        )

        # Build Subject Progress list
        subjects_progress: List[SubjectProgress] = []
        for s in subjects:
            subj_topics = [t for t in topics if t.subject_id == s.id]
            subj_sessions = [sess for sess in sessions if sess.subject_id == s.id]
            subj_completed_sessions = [sess for sess in subj_sessions if sess.status == "completed"]
            subj_quizzes = [
                q for q in quizzes if q.topic_id in [t.id for t in subj_topics]
            ]

            # Average mastery across topics
            avg_mastery = (
                round(sum(t.mastery_score for t in subj_topics) / len(subj_topics), 1)
                if subj_topics
                else 0.0
            )
            avg_quiz = (
                round(sum(q.score for q in subj_quizzes) / len(subj_quizzes), 1)
                if subj_quizzes
                else None
            )

            subjects_progress.append(
                SubjectProgress(
                    subject_id=s.id,
                    subject_name=s.name,
                    subject_code=s.code,
                    color=s.color,
                    mastery=avg_mastery,
                    target_mastery=s.target_mastery,
                    total_topics=len(subj_topics),
                    completed_topics=len([t for t in subj_topics if t.completed]),
                    total_sessions=len(subj_sessions),
                    completed_sessions=len(subj_completed_sessions),
                    total_study_minutes=sum(sess.duration_minutes for sess in subj_completed_sessions),
                    average_quiz_score=avg_quiz,
                )
            )

        # Build Topic Progress list
        topics_progress: List[TopicProgress] = []
        for t in topics:
            parent_subj = next((s for s in subjects if s.id == t.subject_id), None)
            t_rev_count = db.scalar(
                select(func.count(RevisionHistory.id)).where(RevisionHistory.topic_id == t.id)
            ) or 0
            t_quiz_count = len([q for q in quizzes if q.topic_id == t.id])

            topics_progress.append(
                TopicProgress(
                    topic_id=t.id,
                    topic_name=t.name,
                    subject_id=t.subject_id,
                    subject_name=parent_subj.name if parent_subj else "Unknown",
                    difficulty=t.difficulty,
                    mastery_score=t.mastery_score,
                    retention_score=t.retention_score,
                    completed=t.completed,
                    revision_count=t_rev_count,
                    quiz_attempts_count=t_quiz_count,
                    last_revised=t.last_revised,
                    next_revision=t.next_revision,
                )
            )

        completed_topics_count = len([t for t in topics if t.completed])
        overall_progress = (
            round((completed_topics_count / len(topics)) * 100.0, 1) if topics else 0.0
        )

        return OverallProgressStats(
            total_study_minutes=total_study_minutes,
            total_study_hours=round(total_study_minutes / 60.0, 1),
            total_sessions=len(sessions),
            completed_sessions=len(completed_sessions),
            pending_sessions=len(sessions) - len(completed_sessions),
            total_subjects=len(subjects),
            total_topics=len(topics),
            completed_topics=completed_topics_count,
            total_quiz_attempts=len(quizzes),
            average_quiz_accuracy=avg_quiz_accuracy,
            total_revisions=revisions_count,
            overall_progress_percentage=overall_progress,
            subjects_progress=subjects_progress,
            topics_progress=topics_progress,
        )


activity_service = ActivityService()
