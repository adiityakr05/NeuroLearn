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
)
from app.schemas.entities import (
    DailyStudyPlanResponse,
    StudyPlanRescheduleRequest,
    StudyTaskStatusToggleRequest,
    RecommendationCreate,
    RecommendationFeedbackRequest,
    RecommendationStatusUpdate,
    RecommendationsHubResponse,
)
from app.services.activity_service import activity_service


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
        db.commit()
        db.refresh(session)

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

        db.commit()
        db.refresh(session)

        return {
            "success": True,
            "task": activity_service.get_study_session_by_id(db, session.id, user_id),
        }


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

        db.commit()
        db.refresh(rec)
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
        db.commit()
        db.refresh(rec)
        return rec


planner_service = PlannerService()
recommendation_service = RecommendationService()
