
from backend.adaptive_topic_prioritization_service import (
    AdaptiveTopicPrioritizationService,
)


def test_topic_priorities_for_new_user():
    result = AdaptiveTopicPrioritizationService.prioritize_topics(
        "adaptive_priority_empty_user"
    )

    assert result["user_id"] == "adaptive_priority_empty_user"
    assert result["topics"] == []
    assert result["topic_count"] == 0


def test_topic_priorities_rank_critical_reviews():
    result = AdaptiveTopicPrioritizationService.prioritize_topics(
        "recommendation_test_user"
    )

    assert result["topic_count"] >= 1

    topic = result["topics"][0]

    assert topic["topic_id"] == "recommendation_topic_001"
    assert topic["priority_score"] == 100
    assert topic["priority"] == "critical"
    assert topic["predicted_retention_prob"] < 0.60


def test_topic_priorities_are_sorted():
    result = AdaptiveTopicPrioritizationService.prioritize_topics(
        "recommendation_test_user"
    )

    scores = [
        topic["priority_score"]
        for topic in result["topics"]
    ]

    assert scores == sorted(scores, reverse=True)
