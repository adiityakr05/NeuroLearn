
"""
NeuroLearn Adaptive Study Planner
Phase 2.6.3 — Study Session Personalization
"""

from backend.study_planner import StudyPlannerService


class StudySessionService:
    """Generate personalized study sessions from review priorities."""

    @staticmethod
    def generate_session(
        user_id: str,
        total_minutes: int = 30,
    ) -> dict:
        """Create an ordered, time-balanced study session."""

        if total_minutes <= 0:
            raise ValueError("total_minutes must be positive")

        priorities = StudyPlannerService.prioritize_due_reviews(
            user_id
        )

        if not priorities:
            return {
                "user_id": user_id,
                "total_minutes": total_minutes,
                "allocated_minutes": 0,
                "remaining_minutes": total_minutes,
                "sessions": [],
                "count": 0,
            }

        priority_weights = {
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1,
        }

        # Never allocate more topics than available minutes.
        selected_topics = priorities[:total_minutes]

        total_weight = sum(
            priority_weights[item["priority"]]
            for item in selected_topics
        )

        # Guarantee at least one minute per selected topic.
        allocations = [1] * len(selected_topics)
        remaining = total_minutes - len(selected_topics)

        for index, item in enumerate(selected_topics):
            extra = int(
                remaining
                * priority_weights[item["priority"]]
                / total_weight
            )
            allocations[index] += extra

        allocated = sum(allocations)

        # Distribute leftover minutes by urgency.
        leftover = total_minutes - allocated

        for index in range(leftover):
            allocations[index % len(allocations)] += 1

        sessions = []

        for item, minutes in zip(selected_topics, allocations):
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
            "allocated_minutes": sum(allocations),
            "remaining_minutes": total_minutes - sum(allocations),
            "sessions": sessions,
            "count": len(sessions),
        }
