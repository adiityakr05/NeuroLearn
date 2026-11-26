"""
Unit Tests for Performance Agent
"""

from datetime import datetime, timezone, timedelta
import pytest

from app.agents.performance_agent import PerformanceAgent
from app.agents.schemas import (
    StudentContext,
    StudentProfileContext,
    TopicContext,
    SubjectContext,
    ExistingRecommendationContext,
)


@pytest.fixture
def base_student_context():
    ref_time = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)
    profile = StudentProfileContext(
        user_id="usr-1",
        full_name="Bob Learner",
        email="bob@test.com",
        daily_capacity_minutes=90,
    )
    return StudentContext(
        student=profile,
        subjects=[],
        topics=[],
        recent_quizzes=[],
        study_sessions=[],
        active_recommendations=[],
        reference_time=ref_time,
    )


def test_empty_topics_produces_no_recommendations(base_student_context):
    agent = PerformanceAgent()
    recs = agent.run(base_student_context)
    assert len(recs) == 0


def test_prioritizes_low_retention_and_decay(base_student_context):
    """Topic with significant elapsed days and low retention should be prioritized."""
    topic_high_retention = TopicContext(
        id="top-fresh",
        subject_id="sub-1",
        subject_name="AI",
        name="Search Algorithms",
        difficulty="Medium",
        mastery_score=85.0,
        retention_score=95.0,
        decay_rate_lambda=0.08,
        elapsed_days=0.5,
    )
    topic_decayed = TopicContext(
        id="top-decayed",
        subject_id="sub-1",
        subject_name="AI",
        name="Markov Chains",
        difficulty="Medium",
        mastery_score=60.0,
        retention_score=40.0,
        decay_rate_lambda=0.12,
        elapsed_days=15.0,
    )

    base_student_context.topics = [topic_high_retention, topic_decayed]

    agent = PerformanceAgent()
    recs = agent.run(base_student_context, max_recommendations=5)
    assert len(recs) >= 1
    # First recommendation must be the decayed topic
    assert recs[0].topic_id == "top-decayed"
    assert recs[0].type in ["retention_decay", "pacing_optimization"]


def test_exam_urgency_prioritization(base_student_context):
    """Urgent upcoming exam should boost topic to highest priority."""
    topic_distant_exam = TopicContext(
        id="top-distant",
        subject_id="sub-1",
        subject_name="Databases",
        name="SQL Joins",
        difficulty="Easy",
        mastery_score=70.0,
        retention_score=80.0,
        elapsed_days=2.0,
        days_until_exam=45.0,
    )
    topic_imminent_exam = TopicContext(
        id="top-imminent",
        subject_id="sub-2",
        subject_name="Operating Systems",
        name="Virtual Memory & Paging",
        difficulty="Hard",
        mastery_score=50.0,
        retention_score=60.0,
        elapsed_days=2.0,
        days_until_exam=2.0,  # Exam in 2 days!
    )

    base_student_context.topics = [topic_distant_exam, topic_imminent_exam]

    agent = PerformanceAgent()
    recs = agent.run(base_student_context)
    assert len(recs) >= 1
    assert recs[0].topic_id == "top-imminent"
    assert recs[0].priority == "urgent"
    assert recs[0].type == "exam_priority"


def test_daily_study_capacity_constraint(base_student_context):
    """Total recommended duration should not exceed student's daily study capacity."""
    # Capacity is 90 minutes
    base_student_context.student.daily_capacity_minutes = 90

    # 4 Hard topics (60 mins each)
    topics = [
        TopicContext(
            id=f"top-{i}",
            subject_id="sub-1",
            subject_name="CS",
            name=f"Topic {i}",
            difficulty="Hard",
            mastery_score=40.0,
            retention_score=40.0,
            elapsed_days=10.0,
        )
        for i in range(4)
    ]
    base_student_context.topics = topics

    agent = PerformanceAgent()
    recs = agent.run(base_student_context, max_recommendations=10)

    total_allocated = sum(r.estimated_duration_minutes for r in recs)
    assert total_allocated <= base_student_context.student.daily_capacity_minutes
    assert len(recs) <= 2  # 60 + 15 buffer = 75 mins, second 75 mins exceeds 90


def test_prevents_duplicate_recommendations(base_student_context):
    """Topics that already have an active pending recommendation must be skipped."""
    topic_active = TopicContext(
        id="top-pending",
        subject_id="sub-1",
        subject_name="CS",
        name="Sorting Algorithms",
        difficulty="Medium",
        mastery_score=50.0,
        retention_score=30.0,
        elapsed_days=12.0,
    )
    topic_new = TopicContext(
        id="top-new",
        subject_id="sub-1",
        subject_name="CS",
        name="Dynamic Programming",
        difficulty="Hard",
        mastery_score=55.0,
        retention_score=35.0,
        elapsed_days=10.0,
    )

    base_student_context.topics = [topic_active, topic_new]
    # Mark top-pending as already having a pending recommendation
    base_student_context.active_recommendations = [
        ExistingRecommendationContext(
            id="rec-1",
            topic_id="top-pending",
            agent_element="Performance Element",
            type="retention_decay",
            priority="high",
            status="pending",
            title="Review Sorting",
        )
    ]

    agent = PerformanceAgent()
    recs = agent.run(base_student_context)
    recommended_topic_ids = [r.topic_id for r in recs]

    assert "top-pending" not in recommended_topic_ids
    assert "top-new" in recommended_topic_ids
