
"""
NeuroLearn Adaptive Study Planner
Phase 2.6.2 — Study Session Generation
"""

from backend.study_planner import StudyPlannerService


class StudySessionService:
    """Generate personalized study sessions from review priorities."""

    @staticmethod
    def generate_session(
        user_id: str,
        total_minutes: int = 30,
    ) -> dict:
        """Create an ordered study session."""

        if total_minutes <= 0:
            raise ValueError("total_minutes must be positive")

        priorities = StudyPlannerService.prioritize_due_reviews(
            user_id
        )

        if not priorities:
            return {
                "user_id": user_id,
                "total_minutes": total_minutes,
                "sessions": [],
                "count": 0,
            }

        priority_weights = {
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1,
        }

        total_weight = sum(
            priority_weights[item["priority"]]
            for item in priorities
        )

        sessions = []

        allocated_minutes = 0

        for index, item in enumerate(priorities):
            if index == len(priorities) - 1:
                minutes = total_minutes - allocated_minutes
            else:
                minutes = max(
                    1,
                    round(
                        total_minutes
                        * priority_weights[item["priority"]]
                        / total_weight
                    ),
                )

                allocated_minutes += minutes

            sessions.append({
                "topic_id": item["topic_id"],
                "priority": item["priority"],
                "predicted_retention_prob": item[
                    "predicted_retention_prob"
                ],
                "allocated_minutes": minutes,
            })

        return {
            "user_id": user_id,
            "total_minutes": total_minutes,
            "sessions": sessions,
            "count": len(sessions),
        }
