
"""
NeuroLearn Personalized Review Scheduling
Phase 2.5.7
"""

from datetime import datetime, timedelta, timezone


class PersonalizedSchedulingService:
    """Convert predicted retention into a review recommendation."""

    @staticmethod
    def recommend_review_interval(
        predicted_retention_prob: float,
    ) -> int:
        """
        Return recommended review interval in days.
        """

        if not 0.0 <= predicted_retention_prob <= 1.0:
            raise ValueError(
                "Predicted retention probability must be between 0 and 1."
            )

        if predicted_retention_prob < 0.60:
            return 0

        if predicted_retention_prob < 0.75:
            return 1

        if predicted_retention_prob < 0.85:
            return 2

        if predicted_retention_prob < 0.95:
            return 3

        return 7

    @staticmethod
    def build_review_schedule(
        predicted_retention_prob: float,
    user_id: str,
        topic_id: str,
    ) -> dict:

        interval_days = (
            PersonalizedSchedulingService
            .recommend_review_interval(
                predicted_retention_prob
            )
        )

        now = datetime.now(timezone.utc)

        next_review = now + timedelta(
            days=interval_days
        )

        return {
            "user_id": user_id,
            "topic_id": topic_id,
            "predicted_retention_prob": (
                predicted_retention_prob
            ),
            "recommended_interval_days": interval_days,
            "next_review_at": next_review.isoformat(),
            "is_review_due": interval_days == 0,
            "generated_at": now.isoformat(),
        }
