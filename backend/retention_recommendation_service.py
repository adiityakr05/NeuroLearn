
"""
NeuroLearn Adaptive Learning Planner
Phase 2.7.2 — Retention-Aware Recommendations
"""

from backend.study_insights_service import StudyInsightsService
from backend.study_planner import StudyPlannerService
from backend.review_service import ReviewEventService


class RetentionRecommendationService:
    """Generate retention-aware learning recommendations."""

    @staticmethod
    def get_recommendations(user_id: str) -> dict:
        """Generate personalized recommendations from learner data."""

        history = ReviewEventService.get_user_history(user_id)
        due_reviews = StudyPlannerService.prioritize_due_reviews(user_id)
        weak_topics = StudyInsightsService.get_weak_topics(user_id)

        recommendations = []

        # Prioritize topics requiring immediate review.
        for review in due_reviews:
            retention = review["predicted_retention_prob"]

            if retention < 0.60:
                reason = "Retention is critically low."
                priority = "critical"
            elif retention < 0.75:
                reason = "Retention is low; review soon."
                priority = "high"
            else:
                reason = "Scheduled review is due."
                priority = review["priority"]

            recommendations.append({
                "topic_id": review["topic_id"],
                "type": "retention_review",
                "priority": priority,
                "predicted_retention_prob": retention,
                "reason": reason,
            })

        # Add recommendations for weak topics not already included.
        recommended_topics = {
            item["topic_id"] for item in recommendations
        }

        for topic in weak_topics.get("topics", []):
            topic_id = topic["topic_id"]

            if topic_id in recommended_topics:
                continue

            recommendations.append({
                "topic_id": topic_id,
                "type": "weak_topic_review",
                "priority": "high",
                "reason": "This topic is identified as a learning weakness.",
            })

        priority_order = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3,
        }

        recommendations.sort(
            key=lambda item: priority_order[item["priority"]]
        )

        return {
            "user_id": user_id,
            "recommendations": recommendations,
            "recommendation_count": len(recommendations),
            "review_history": history,
        }
