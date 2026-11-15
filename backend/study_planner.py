
"""
NeuroLearn Adaptive Study Planner
Phase 2.6.1 — Due-Review Prioritization
"""

from datetime import datetime, timezone

from backend.schedule_repository import ScheduleRepository


class StudyPlannerService:
    """Prioritize topics using their review schedules."""

    @staticmethod
    def prioritize_due_reviews(user_id: str) -> list[dict]:
        """Return due reviews ordered by urgency."""

        schedules = ScheduleRepository.get_due_schedules(user_id)

        prioritized = []

        for schedule in schedules:
            retention = schedule["predicted_retention_prob"]

            if retention < 0.60:
                priority = "critical"
            elif retention < 0.75:
                priority = "high"
            elif retention < 0.85:
                priority = "medium"
            else:
                priority = "low"

            prioritized.append({
                "user_id": schedule["user_id"],
                "topic_id": schedule["topic_id"],
                "predicted_retention_prob": retention,
                "next_review_at": schedule["next_review_at"],
                "priority": priority,
            })

        priority_order = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3,
        }

        prioritized.sort(
            key=lambda item: (
                priority_order[item["priority"]],
                item["predicted_retention_prob"],
                item["next_review_at"],
            )
        )

        return prioritized
