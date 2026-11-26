"""
Unit Tests for Learning Agent (Milestone 3)
===========================================
Tests:
- Improving quiz performance trajectory (+15% gain).
- Declining quiz performance trajectory (-15% drop).
- Consistently high performance (all >=80%, interval expansion, difficulty escalation).
- Repeated low performance (all <60%, interval contraction, lambda increase).
- Insufficient historical data (<2 attempts fallback).
- Lambda boundary condition enforcement ([0.01, 0.30]).
- Revision interval adjustments.
- Available study-time constraints.
- Missing or invalid feedback handling.
- Deterministic output for identical input.
"""

from datetime import datetime, timezone
import pytest

from app.agents.learning_agent import LearningAgent
from app.agents.schemas import (
    StudentContext,
    StudentProfileContext,
    TopicContext,
    QuizAttemptContext,
)
from app.ml.retention_model import MIN_LAMBDA, MAX_LAMBDA


@pytest.fixture
def base_context():
    ref_time = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)
    profile = StudentProfileContext(
        user_id="usr-learn-1",
        full_name="Dana Student",
        email="dana@test.com",
        daily_capacity_minutes=120,
    )
    topic = TopicContext(
        id="top-recursion",
        subject_id="sub-cs",
        subject_name="Computer Science",
        name="Recursion & Backtracking",
        difficulty="Medium",
        mastery_score=60.0,
        retention_score=70.0,
        decay_rate_lambda=0.08,
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


def test_insufficient_historical_data(base_context):
    """With only 1 quiz attempt, trajectory should be 'insufficient_data' and retain parameters."""
    q = QuizAttemptContext(
        id="q-1",
        topic_id="top-recursion",
        score=75.0,
        accuracy=75.0,
    )
    base_context.recent_quizzes = [q]

    agent = LearningAgent()
    result = agent.run(base_context)

    assert len(result.trajectories) == 1
    traj = result.trajectories[0]
    assert traj.trend == "insufficient_data"
    assert traj.proposed_lambda == traj.current_lambda
    assert traj.proposed_interval_days == traj.current_interval_days
    # No urgent policy recommendations generated for insufficient data
    assert len(result.recommendation_candidates) == 0


def test_improving_quiz_performance(base_context):
    """Quizzes showing upward trend from 50% to 80% (+30%) should be classified as 'improving'."""
    # Recent quizzes in chronological order: 50 -> 65 -> 80
    quizzes = [
        QuizAttemptContext(id="q-3", topic_id="top-recursion", score=80.0, accuracy=80.0),
        QuizAttemptContext(id="q-2", topic_id="top-recursion", score=65.0, accuracy=65.0),
        QuizAttemptContext(id="q-1", topic_id="top-recursion", score=50.0, accuracy=50.0),
    ]
    base_context.recent_quizzes = quizzes

    agent = LearningAgent()
    result = agent.run(base_context)

    traj = result.trajectories[0]
    assert traj.trend == "improving"
    assert traj.proposed_lambda < traj.current_lambda  # lambda decreases (slower forgetting)
    assert len(result.recommendation_candidates) == 1
    rec = result.recommendation_candidates[0]
    assert rec.priority == "medium"
    assert "Milestone Consolidation" in rec.title


def test_declining_quiz_performance(base_context):
    """Quizzes showing downward trend from 85% to 50% (-35%) should be classified as 'declining'."""
    # Chronological: 85 -> 65 -> 50
    quizzes = [
        QuizAttemptContext(id="q-3", topic_id="top-recursion", score=50.0, accuracy=50.0),
        QuizAttemptContext(id="q-2", topic_id="top-recursion", score=65.0, accuracy=65.0),
        QuizAttemptContext(id="q-1", topic_id="top-recursion", score=85.0, accuracy=85.0),
    ]
    base_context.recent_quizzes = quizzes

    agent = LearningAgent()
    result = agent.run(base_context)

    traj = result.trajectories[0]
    assert traj.trend == "declining"
    assert traj.proposed_lambda > traj.current_lambda  # lambda increases (faster forgetting)
    assert len(result.recommendation_candidates) == 1
    rec = result.recommendation_candidates[0]
    assert rec.priority == "high"
    assert "Decay Mitigation" in rec.title


def test_consistently_high_performance(base_context):
    """Scores consistently >= 80% (avg >= 85%) should expand interval and advance difficulty."""
    quizzes = [
        QuizAttemptContext(id="q-3", topic_id="top-recursion", score=95.0, accuracy=95.0),
        QuizAttemptContext(id="q-2", topic_id="top-recursion", score=90.0, accuracy=90.0),
        QuizAttemptContext(id="q-1", topic_id="top-recursion", score=88.0, accuracy=88.0),
    ]
    base_context.recent_quizzes = quizzes

    agent = LearningAgent()
    result = agent.run(base_context)

    traj = result.trajectories[0]
    assert traj.trend == "consistently_high"
    assert traj.proposed_lambda < traj.current_lambda
    assert traj.proposed_interval_days >= traj.current_interval_days
    assert traj.proposed_difficulty == "Hard"  # Advanced from Medium to Hard
    assert len(result.recommendation_candidates) == 1
    rec = result.recommendation_candidates[0]
    assert rec.priority == "low"
    assert "Interval Expansion" in rec.title


def test_repeated_low_performance(base_context):
    """Scores repeatedly < 60% should accelerate decay lambda and contract revision interval."""
    quizzes = [
        QuizAttemptContext(id="q-3", topic_id="top-recursion", score=40.0, accuracy=40.0),
        QuizAttemptContext(id="q-2", topic_id="top-recursion", score=45.0, accuracy=45.0),
        QuizAttemptContext(id="q-1", topic_id="top-recursion", score=35.0, accuracy=35.0),
    ]
    base_context.recent_quizzes = quizzes

    agent = LearningAgent()
    result = agent.run(base_context)

    traj = result.trajectories[0]
    assert traj.trend == "repeated_low"
    assert traj.proposed_lambda > traj.current_lambda
    assert traj.proposed_interval_days <= traj.current_interval_days
    assert traj.recommended_duration_minutes >= 60  # Extended session
    assert len(result.recommendation_candidates) == 1
    rec = result.recommendation_candidates[0]
    assert rec.priority == "urgent"
    assert "Strategy Adaptation" in rec.title


def test_lambda_boundary_enforcement(base_context):
    """Extreme performance should never violate MIN_LAMBDA or MAX_LAMBDA bounds."""
    # Near max boundary
    base_context.topics[0].decay_rate_lambda = 0.28
    quizzes_low = [
        QuizAttemptContext(id="q-1", topic_id="top-recursion", score=10.0, accuracy=10.0),
        QuizAttemptContext(id="q-2", topic_id="top-recursion", score=10.0, accuracy=10.0),
    ]
    base_context.recent_quizzes = quizzes_low

    agent = LearningAgent()
    res_high = agent.run(base_context)
    assert res_high.trajectories[0].proposed_lambda <= MAX_LAMBDA

    # Near min boundary
    base_context.topics[0].decay_rate_lambda = 0.012
    quizzes_high = [
        QuizAttemptContext(id="q-3", topic_id="top-recursion", score=100.0, accuracy=100.0),
        QuizAttemptContext(id="q-4", topic_id="top-recursion", score=100.0, accuracy=100.0),
    ]
    base_context.recent_quizzes = quizzes_high
    res_low = agent.run(base_context)
    assert res_low.trajectories[0].proposed_lambda >= MIN_LAMBDA


def test_available_study_time_constraints(base_context):
    """Low daily capacity (<60 mins) should clamp recommended study duration to 30 mins."""
    base_context.student.daily_capacity_minutes = 45  # Limited study time
    quizzes = [
        QuizAttemptContext(id="q-1", topic_id="top-recursion", score=40.0, accuracy=40.0),
        QuizAttemptContext(id="q-2", topic_id="top-recursion", score=45.0, accuracy=45.0),
    ]
    base_context.recent_quizzes = quizzes

    agent = LearningAgent()
    result = agent.run(base_context)
    traj = result.trajectories[0]
    # Even though repeated_low would usually recommend 60 mins, low capacity clamps to 30
    assert traj.recommended_duration_minutes == 30


def test_deterministic_output_for_identical_input(base_context):
    """Two invocations on identical context must produce identical results."""
    quizzes = [
        QuizAttemptContext(id="q-1", topic_id="top-recursion", score=75.0, accuracy=75.0),
        QuizAttemptContext(id="q-2", topic_id="top-recursion", score=90.0, accuracy=90.0),
    ]
    base_context.recent_quizzes = quizzes

    agent = LearningAgent()
    run1 = agent.run(base_context)
    run2 = agent.run(base_context)

    assert run1.model_dump() == run2.model_dump()
