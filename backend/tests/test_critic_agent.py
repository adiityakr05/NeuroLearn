"""
Unit Tests for Critic Agent
"""

from datetime import datetime, timezone
import pytest

from app.agents.critic_agent import CriticAgent
from app.agents.schemas import (
    StudentContext,
    StudentProfileContext,
    QuizAttemptContext,
    TopicContext,
)


@pytest.fixture
def base_student_context():
    ref_time = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)
    profile = StudentProfileContext(
        user_id="usr-critic-1",
        full_name="Charlie Student",
        email="charlie@test.com",
    )
    topic = TopicContext(
        id="top-tree",
        subject_id="sub-algo",
        subject_name="Algorithms",
        name="Binary Search Trees",
        mastery_score=50.0,
        retention_score=60.0,
    )
    return StudentContext(
        student=profile,
        subjects=[],
        topics=[topic],
        recent_quizzes=[],
        study_sessions=[],
        active_recommendations=[],
        reference_time=ref_time,
    )


def test_critic_classifies_high_concern(base_student_context):
    """Scores below 60% must be classified as 'High Concern' and flag needs_practice=True."""
    quiz = QuizAttemptContext(
        id="quiz-fail",
        topic_id="top-tree",
        topic_name="Binary Search Trees",
        score=45.0,
        accuracy=45.0,
        total_questions=10,
        correct_answers=4,
        critic_evaluated=False,
    )
    base_student_context.recent_quizzes = [quiz]

    agent = CriticAgent()
    evaluations = agent.run(base_student_context)
    assert len(evaluations) == 1

    res = evaluations[0]
    assert res.performance_category == "High Concern"
    assert res.concern_level == "high"
    assert res.needs_practice is True
    assert "High Concern" in res.critic_notes
    assert res.recommendation_candidate is not None
    assert res.recommendation_candidate.priority == "urgent"
    assert res.recommendation_candidate.agent_element == "Critic"


def test_critic_classifies_moderate_concern(base_student_context):
    """Scores between 60% and 80% must be classified as 'Moderate Concern'."""
    quiz = QuizAttemptContext(
        id="quiz-mid",
        topic_id="top-tree",
        topic_name="Binary Search Trees",
        score=70.0,
        accuracy=70.0,
        total_questions=10,
        correct_answers=7,
        critic_evaluated=False,
    )
    base_student_context.recent_quizzes = [quiz]

    agent = CriticAgent()
    evaluations = agent.run(base_student_context)
    assert len(evaluations) == 1

    res = evaluations[0]
    assert res.performance_category == "Moderate Concern"
    assert res.concern_level == "moderate"
    assert res.needs_practice is True
    assert "Moderate Concern" in res.critic_notes
    assert res.recommendation_candidate is not None
    assert res.recommendation_candidate.priority == "medium"


def test_critic_classifies_reinforcement(base_student_context):
    """Scores above 80% must be classified as 'Reinforcement' with no urgent remedial recommendation."""
    quiz = QuizAttemptContext(
        id="quiz-high",
        topic_id="top-tree",
        topic_name="Binary Search Trees",
        score=90.0,
        accuracy=90.0,
        total_questions=10,
        correct_answers=9,
        critic_evaluated=False,
    )
    base_student_context.recent_quizzes = [quiz]

    agent = CriticAgent()
    evaluations = agent.run(base_student_context)
    assert len(evaluations) == 1

    res = evaluations[0]
    assert res.performance_category == "Reinforcement"
    assert res.concern_level == "low"
    assert res.needs_practice is False
    assert "Reinforcement" in res.critic_notes
    # Reinforcement should not spawn an urgent remediation recommendation
    assert res.recommendation_candidate is None


def test_critic_filters_already_evaluated_quizzes(base_student_context):
    """When unevaluated_only=True, attempts with critic_evaluated=True should be ignored."""
    quiz_done = QuizAttemptContext(
        id="quiz-done",
        topic_id="top-tree",
        score=50.0,
        accuracy=50.0,
        critic_evaluated=True,
    )
    quiz_pending = QuizAttemptContext(
        id="quiz-pending",
        topic_id="top-tree",
        score=55.0,
        accuracy=55.0,
        critic_evaluated=False,
    )
    base_student_context.recent_quizzes = [quiz_done, quiz_pending]

    agent = CriticAgent()
    evaluations = agent.run(base_student_context, unevaluated_only=True)
    assert len(evaluations) == 1
    assert evaluations[0].attempt_id == "quiz-pending"
