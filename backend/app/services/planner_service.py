from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func

from app.models.entities import (
    StudySession,
    Recommendation,
    Subject,
    Topic,
    RevisionHistory,
)
from app.schemas.entities import (
    DailyStudyPlanResponse,
    StudyPlanRescheduleRequest,
    StudyTaskStatusToggleRequest,
    RecommendationCreate,
    RecommendationFeedbackRequest,
    RecommendationStatusUpdate,
    RecommendationsHubResponse,
    SpacedRepetitionItemResponse,
)
from app.services.activity_service import activity_service
from app.ml.retention_model import RetentionModel, DEFAULT_TARGET_RETENTION


class PlannerService:
    @staticmethod
    def get_daily_study_plan(db: Session, user_id: str, date: str) -> Dict[str, Any]:
        """
        Retrieves daily schedule for the authenticated student on a specific date.
        """
        sessions = activity_service.get_study_sessions(
            db, user_id=user_id, start_date=date, end_date=date
        )
        total_sessions = len(sessions)
        completed_sessions = len([s for s in sessions if s["status"] == "completed"])
        total_minutes = sum(s["duration_minutes"] for s in sessions)

        return {
            "date": date,
            "sessions": sessions,
            "totalSessions": total_sessions,
            "completedSessions": completed_sessions,
            "totalMinutes": total_minutes,
        }

    @staticmethod
    def get_week_study_plan(db: Session, user_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves weekly study schedule for the student.
        """
        return activity_service.get_study_sessions(db, user_id=user_id, limit=200)

    @staticmethod
    def toggle_task_status(
        db: Session,
        user_id: str,
        toggle_in: StudyTaskStatusToggleRequest,
    ) -> Dict[str, Any]:
        task_id = toggle_in.taskId or toggle_in.task_id
        if not task_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="taskId is required",
            )
        session = db.scalar(
            select(StudySession).where(StudySession.id == task_id, StudySession.user_id == user_id)
        )
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Study task not found",
            )

        session.status = toggle_in.status
        if toggle_in.status == "completed":
            session.completed_at = datetime.now(timezone.utc)
            if not session.started_at:
                session.started_at = session.completed_at
            if toggle_in.actual_duration_minutes is not None:
                session.actual_duration_minutes = toggle_in.actual_duration_minutes
            elif session.actual_duration_minutes is None:
                diff_minutes = int((session.completed_at - session.started_at).total_seconds() / 60)
                session.actual_duration_minutes = max(0, diff_minutes)
        elif toggle_in.status == "in_progress":
            if not session.started_at:
                session.started_at = datetime.now(timezone.utc)
        elif toggle_in.status == "abandoned":
            if not session.started_at:
                session.started_at = datetime.now(timezone.utc)
            if toggle_in.actual_duration_minutes is not None:
                session.actual_duration_minutes = toggle_in.actual_duration_minutes
        try:
            db.commit()
            db.refresh(session)
        except Exception:
            db.rollback()
            raise

        return {
            "success": True,
            "taskId": session.id,
            "newStatus": session.status,
            "task": activity_service.get_study_session_by_id(db, session.id, user_id),
        }

    @staticmethod
    def reschedule_task(
        db: Session,
        user_id: str,
        reschedule_in: StudyPlanRescheduleRequest,
    ) -> Dict[str, Any]:
        task_id = reschedule_in.taskId or reschedule_in.task_id
        new_date = reschedule_in.newDate or reschedule_in.new_date
        new_slot = reschedule_in.newSlot or reschedule_in.new_slot

        if not task_id or not new_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="taskId and newDate are required for rescheduling",
            )

        session = db.scalar(
            select(StudySession).where(StudySession.id == task_id, StudySession.user_id == user_id)
        )
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Study task not found",
            )

        session.date = new_date
        if new_slot:
            session.time_slot = new_slot
        if reschedule_in.reason:
            session.ai_reason = f"Rescheduled: {reschedule_in.reason}"

        try:
            db.commit()
            db.refresh(session)
        except Exception:
            db.rollback()
            raise

        return {
            "success": True,
            "task": activity_service.get_study_session_by_id(db, session.id, user_id),
        }

    @staticmethod
    def get_spaced_repetition_queue(
        db: Session,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Calculates and returns the spaced repetition review queue for the authenticated student.
        Uses the ML Retention Engine (Ebbinghaus forgetting curve) based on elapsed time and lambda.
        Purely read-only: does not modify topics or database records.
        """
        # Fetch all topics belonging to the student's subjects
        topics = db.scalars(
            select(Topic)
            .join(Subject, Topic.subject_id == Subject.id)
            .where(Subject.user_id == user_id)
        ).all()

        if not topics:
            return []

        retention_model = RetentionModel()
        now = datetime.now(timezone.utc)

        queue = []
        for topic in topics:
            subject = topic.subject
            subject_name = subject.name if subject else "General"

            # Repetition cycle count
            revision_count = len(topic.revision_history) if topic.revision_history else 0
            cycle = revision_count + 1

            # Determine reference date for elapsed time
            ref_dt = topic.last_revised or topic.created_at
            if ref_dt:
                if ref_dt.tzinfo is None:
                    ref_dt = ref_dt.replace(tzinfo=timezone.utc)
                elapsed_days = (now - ref_dt).total_seconds() / 86400.0
                if elapsed_days < 0.0:
                    elapsed_days = 0.0
            else:
                elapsed_days = 0.0

            # Calculate current retention using ML engine
            decay_lambda = topic.decay_rate_lambda or 0.08
            retention_score = retention_model.calculate_retention(elapsed_days, decay_lambda)

            # Scheduled date: if next_revision exists use it, else calculate from model
            scheduled_date_str = None
            days_until_scheduled = None
            if topic.next_revision:
                nr_dt = topic.next_revision
                if nr_dt.tzinfo is None:
                    nr_dt = nr_dt.replace(tzinfo=timezone.utc)
                scheduled_date_str = nr_dt.strftime("%Y-%m-%d")
                days_until_scheduled = (nr_dt.date() - now.date()).days
            else:
                rec_interval = retention_model.calculate_recommended_interval(decay_lambda, DEFAULT_TARGET_RETENTION)
                import datetime as dt_mod
                sched_target = (ref_dt or now) + dt_mod.timedelta(days=rec_interval)
                scheduled_date_str = sched_target.strftime("%Y-%m-%d")
                days_until_scheduled = (sched_target.date() - now.date()).days

            # Determine urgency and repetitionStage string
            # Critical: retention < 65% or overdue by >= 2 days
            # Warning: retention < 75% or due today / overdue by 1 day
            # Optimal: retention < 85% or due soon
            # Retained: retention >= 85%
            if days_until_scheduled is not None and days_until_scheduled < 0:
                overdue_days = abs(days_until_scheduled)
                urgency = "critical" if (overdue_days >= 2 or retention_score < 65.0) else "warning"
                stage_label = f"Interval {cycle} (Overdue by {overdue_days}d)"
            elif days_until_scheduled is not None and days_until_scheduled == 0:
                urgency = "critical" if retention_score < 65.0 else "warning"
                stage_label = f"Interval {cycle} (Due Today)"
            elif retention_score < 65.0:
                urgency = "critical"
                stage_label = f"Interval {cycle} (Critical Recall)"
            elif retention_score < 75.0:
                urgency = "warning"
                stage_label = f"Interval {cycle} (Review Due)"
            elif retention_score < 85.0:
                urgency = "optimal"
                stage_label = f"Interval {cycle} (Optimal)"
            else:
                urgency = "retained"
                stage_label = f"Interval {cycle} (Retained)"

            # Exam weight based on topic difficulty
            if topic.difficulty == "Hard":
                exam_weight = "High (20%)"
            elif topic.difficulty == "Medium":
                exam_weight = "Medium (15%)"
            else:
                exam_weight = "Normal (10%)"

            last_rev_str = topic.last_revised.strftime("%Y-%m-%d") if topic.last_revised else None
            next_rev_str = topic.next_revision.strftime("%Y-%m-%d") if topic.next_revision else scheduled_date_str

            item = {
                "id": f"sr_{topic.id}",
                "topic_id": topic.id,
                "subject_id": topic.subject_id,
                "topic": topic.name,
                "subject": subject_name,
                "daysSinceReview": round(elapsed_days, 1),
                "estimatedRetention": round(retention_score, 1),
                "urgency": urgency,
                "repetitionStage": stage_label,
                "scheduledDate": scheduled_date_str,
                "examWeight": exam_weight,
                "decayRateLambda": round(decay_lambda, 4),
                "lastRevised": last_rev_str,
                "nextRevision": next_rev_str,
                # snake_case copies for API consistency
                "days_since_review": round(elapsed_days, 1),
                "estimated_retention": round(retention_score, 1),
                "decay_rate_lambda": round(decay_lambda, 4),
                "last_revised": last_rev_str,
                "next_revision": next_rev_str,
                "repetition_stage": stage_label,
                "scheduled_date": scheduled_date_str,
                "exam_weight": exam_weight,
            }
            queue.append(item)

        # Priority sort order:
        # Urgency priority: critical (0) > warning (1) > optimal (2) > retained (3)
        # Secondary: lowest estimatedRetention first
        # Tertiary: highest daysSinceReview first
        urgency_rank = {"critical": 0, "warning": 1, "optimal": 2, "retained": 3}
        queue.sort(
            key=lambda x: (
                urgency_rank.get(x["urgency"], 4),
                x["estimatedRetention"],
                -x["daysSinceReview"],
            )
        )

        return queue


class RecommendationService:
    @staticmethod
    def get_recommendations(
        db: Session,
        user_id: str,
        status_filter: Optional[str] = None,
        agent_element: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Recommendation]:
        """
        Lists recommendations owned by student with optional status/element filters.
        """
        query = select(Recommendation).where(Recommendation.user_id == user_id)
        if status_filter:
            query = query.where(Recommendation.status == status_filter)
        if agent_element:
            query = query.where(Recommendation.agent_element == agent_element)

        query = query.order_by(Recommendation.created_at.desc()).offset(skip).limit(limit)
        return list(db.scalars(query).all())

    @staticmethod
    def get_recommendation_by_id(
        db: Session,
        recommendation_id: str,
        user_id: str,
    ) -> Recommendation:
        rec = db.scalar(
            select(Recommendation).where(
                Recommendation.id == recommendation_id,
                Recommendation.user_id == user_id,
            )
        )
        if not rec:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recommendation not found",
            )
        return rec

    @staticmethod
    def generate_fresh_recommendations(
        db: Session,
        user_id: str,
        max_recommendations: int = 5,
    ) -> List[Recommendation]:
        """
        Explicitly triggers the AI Orchestrator to synthesize fresh recommendations
        and persists new non-duplicate candidates to the database.
        """
        from app.agents.orchestrator import ai_orchestrator
        from app.agents.orchestrator_schemas import ExecutionMode

        # Run orchestrator in RECOMMENDATION mode
        result = ai_orchestrator.run(
            db=db,
            user_id=user_id,
            mode=ExecutionMode.RECOMMENDATION,
            max_recommendations=max_recommendations,
        )

        # Existing pending recommendations for user
        existing_pending = list(
            db.scalars(
                select(Recommendation).where(
                    Recommendation.user_id == user_id,
                    Recommendation.status == "pending",
                )
            ).all()
        )
        existing_keys = {(r.topic_id, r.type) for r in existing_pending if r.topic_id}

        persisted: List[Recommendation] = []
        for cand in result.recommendations:
            if cand.topic_id and (cand.topic_id, cand.type) in existing_keys:
                continue

            new_rec = Recommendation(
                user_id=user_id,
                subject_id=cand.subject_id,
                topic_id=cand.topic_id,
                agent_element=cand.agent_element,
                type=cand.type,
                priority=cand.priority,
                title=cand.title,
                reason_type=cand.reason_type,
                reason_detail=cand.reason_detail,
                suggested_slot=cand.suggested_slot or "Flexible",
                estimated_duration_minutes=cand.estimated_duration_minutes,
                status="pending",
            )
            db.add(new_rec)
            persisted.append(new_rec)
            if cand.topic_id:
                existing_keys.add((cand.topic_id, cand.type))

        if persisted:
            try:
                db.commit()
                for r in persisted:
                    db.refresh(r)
            except Exception:
                db.rollback()
                raise

        return persisted

    @staticmethod
    def get_recommendations_hub(db: Session, user_id: str) -> Dict[str, Any]:
        """
        Returns recommendations grouped for the frontend Recommendations Hub:
        - activeRecommendations (pending)
        - history (accepted / dismissed / completed)
        - countsByElement
        - totalPending
        """
        all_recs = list(
            db.scalars(
                select(Recommendation)
                .where(Recommendation.user_id == user_id)
                .order_by(Recommendation.created_at.desc())
            ).all()
        )

        active = [r for r in all_recs if r.status == "pending"]
        history = [r for r in all_recs if r.status != "pending"]

        counts = {
            "Performance Element": len([r for r in active if r.agent_element == "Performance Element"]),
            "Critic": len([r for r in active if r.agent_element == "Critic"]),
            "Learning Element": len([r for r in active if r.agent_element == "Learning Element"]),
            "Problem Generator": len([r for r in active if r.agent_element == "Problem Generator"]),
        }

        return {
            "activeRecommendations": active,
            "history": history,
            "countsByElement": counts,
            "totalPending": len(active),
        }

    @staticmethod
    def update_recommendation_status(
        db: Session,
        recommendation_id: str,
        user_id: str,
        status_in: RecommendationStatusUpdate,
    ) -> Recommendation:
        rec = RecommendationService.get_recommendation_by_id(db, recommendation_id, user_id)
        rec.status = status_in.status
        if status_in.student_adherence:
            rec.student_adherence = status_in.student_adherence

        # If accepted, schedule study task automatically
        if status_in.status == "accepted" and rec.subject_id:
            from app.models.entities import StudySession
            new_task = StudySession(
                user_id=user_id,
                subject_id=rec.subject_id,
                topic_id=rec.topic_id,
                date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                time_slot=rec.suggested_slot or "Flexible",
                duration_minutes=rec.estimated_duration_minutes,
                status="pending",
                priority=rec.priority,
                ai_reason=f"Scheduled from {rec.agent_element} recommendation: {rec.title}",
            )
            db.add(new_task)

        try:
            db.commit()
            db.refresh(rec)
        except Exception:
            db.rollback()
            raise
        return rec

    @staticmethod
    def record_feedback(
        db: Session,
        recommendation_id: str,
        user_id: str,
        feedback_in: RecommendationFeedbackRequest,
    ) -> Recommendation:
        rec = RecommendationService.get_recommendation_by_id(db, recommendation_id, user_id)
        rec.feedback_helpful = feedback_in.helpful
        if feedback_in.note:
            rec.feedback_note = feedback_in.note
        try:
            db.commit()
            db.refresh(rec)
        except Exception:
            db.rollback()
            raise
        return rec


planner_service = PlannerService()
recommendation_service = RecommendationService()
