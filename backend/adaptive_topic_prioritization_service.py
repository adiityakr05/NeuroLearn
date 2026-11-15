
"""
NeuroLearn Adaptive Learning Planner
Phase 2.7.3 — Adaptive Topic Prioritization
"""

from backend.study_insights_service import StudyInsightsService
from backend.study_planner import StudyPlannerService
from backend.review_service import ReviewEventService


class AdaptiveTopicPrioritizationService:
    """Rank learning topics using retention and learning performance."""

    @staticmethod
    def prioritize_topics(user_id: str) -> dict:
        """Generate an adaptive priority ranking for learner topics."""

        due_reviews = StudyPlannerService.prioritize_due_reviews(user_id)
        weak_topics = StudyInsightsService.get_weak_topics(user_id)
        history = ReviewEventService.get_user_history(user_id)

        topic_scores = {}

        # Add retention-based urgency.
        for review in due_reviews:
            topic_id = review["topic_id"]
            retention = review["predicted_retention_prob"]

            if retention < 0.60:
                score = 100
                priority = "critical"
            elif retention < 0.75:
                score = 80
                priority = "high"
            elif retention < 0.85:
                score = 60
                priority = "medium"
            else:
                score = 40
                priority = "low"

            topic_scores[topic_id] = {
                "topic_id": topic_id,
                "priority_score": score,
                "priority": priority,
                "predicted_retention_prob": retention,
                "reasons": ["Retention-based review urgency"],
            }

        # Add weakness-based priority.
        for topic in weak_topics.get("topics", []):
            topic_id = topic["topic_id"]

            if topic_id not in topic_scores:
                topic_scores[topic_id] = {
                    "topic_id": topic_id,
                    "priority_score": 70,
                    "priority": "high",
                    "predicted_retention_prob": None,
                    "reasons": [],
                }

            topic_scores[topic_id]["priority_score"] += 20
            topic_scores[topic_id]["reasons"].append(
                "Identified as a weak learning topic"
            )

        # Include topics with review history.
        for topic in history.get("topics", []):
            topic_id = topic["topic_id"]

            if topic_id not in topic_scores:
                topic_scores[topic_id] = {
                    "topic_id": topic_id,
                    "priority_score": 30,
                    "priority": "low",
                    "predicted_retention_prob": None,
                    "reasons": ["Previously studied topic"],
                }

        # Final priority classification.
        for item in topic_scores.values():
            score = item["priority_score"]

            if score >= 100:
                item["priority"] = "critical"
            elif score >= 80:
                item["priority"] = "high"
            elif score >= 60:
                item["priority"] = "medium"
            else:
                item["priority"] = "low"

        ranked_topics = sorted(
            topic_scores.values(),
            key=lambda item: item["priority_score"],
            reverse=True,
        )

        return {
            "user_id": user_id,
            "topics": ranked_topics,
            "topic_count": len(ranked_topics),
        }

