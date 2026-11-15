
from backend.retention_recommendation_service import (
    RetentionRecommendationService,
)


def test_recommendations_for_new_user():
    result = RetentionRecommendationService.get_recommendations(
        "recommendation_empty_test"
    )

    assert result["user_id"] == "recommendation_empty_test"
    assert result["recommendations"] == []
    assert result["recommendation_count"] == 0


def test_recommendations_include_due_reviews():
    result = RetentionRecommendationService.get_recommendations(
        "recommendation_test_user"
    )

    assert result["recommendation_count"] >= 1

    recommendation = result["recommendations"][0]

    assert recommendation["topic_id"] == "recommendation_topic_001"
    assert recommendation["type"] == "retention_review"
    assert recommendation["priority"] == "critical"
    assert recommendation["predicted_retention_prob"] < 0.60


def test_recommendations_include_review_history():
    result = RetentionRecommendationService.get_recommendations(
        "recommendation_test_user"
    )

    history = result["review_history"]

    assert history["total_review_count"] >= 1
    assert history["overall_recall_rate"] == 0.0
