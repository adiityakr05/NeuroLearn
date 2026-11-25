"""
Integration Tests for Database Transaction Safety & Recommendation Hub
======================================================================
Tests:
- Task 1: Database write rollback on simulated failures (Quiz submission, Study session update).
- Task 2: Explicit recommendation generation flow, deduplication, and non-overwriting.
- Task 4: Recommendation Hub response structure, active vs historical items, 4-element grouping,
          total pending count, and tenant ownership isolation.
"""

from datetime import datetime, timezone
from unittest.mock import patch
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.entities import User, Subject, Topic, QuizAttempt, StudySession, Recommendation
from app.services.activity_service import ActivityService
from app.services.planner_service import RecommendationService
from app.schemas.entities import QuizAttemptCreate, StudySessionCreate, RecommendationStatusUpdate


# ==============================================================================
# TASK 1: DATABASE TRANSACTION SAFETY TESTS
# ==============================================================================

def test_quiz_attempt_creation_rollback_on_commit_failure(db_session):
    """Simulates a database commit error during quiz creation and confirms rollback."""
    user = User(id="usr-tx-1", email="tx1@test.com", hashed_password="pw", full_name="User TX1")
    subj = Subject(id="sub-tx-1", user_id="usr-tx-1", name="Math", code="M101")
    topic = Topic(id="top-tx-1", subject_id="sub-tx-1", name="Algebra", mastery_score=50.0)
    db_session.add_all([user, subj, topic])
    db_session.commit()

    attempt_in = QuizAttemptCreate(
        topic_id="top-tx-1",
        title="Algebra Quiz",
        total_questions=10,
        correct_answers=8,
    )

    # Patch db_session.commit to raise an exception
    with patch.object(db_session, "commit", side_effect=RuntimeError("Simulated DB lock contention")):
        with pytest.raises(RuntimeError, match="Simulated DB lock contention"):
            ActivityService.create_quiz_attempt(
                db=db_session,
                user_id="usr-tx-1",
                attempt_in=attempt_in,
            )

    # Ensure no dirty quiz attempt was committed
    attempts = list(db_session.scalars(select(QuizAttempt).where(QuizAttempt.user_id == "usr-tx-1")).all())
    assert len(attempts) == 0

    # Ensure session is still usable
    refreshed_topic = db_session.scalar(select(Topic).where(Topic.id == "top-tx-1"))
    assert refreshed_topic is not None


def test_study_session_creation_rollback_on_failure(db_session):
    """Simulates a database commit error during study session creation and confirms rollback."""
    user = User(id="usr-tx-2", email="tx2@test.com", hashed_password="pw", full_name="User TX2")
    subj = Subject(id="sub-tx-2", user_id="usr-tx-2", name="Science", code="SCI1")
    db_session.add_all([user, subj])
    db_session.commit()

    session_in = StudySessionCreate(
        subject_id="sub-tx-2",
        date="2026-11-25",
        duration_minutes=45,
    )

    with patch.object(db_session, "commit", side_effect=RuntimeError("Simulated IO Error")):
        with pytest.raises(RuntimeError, match="Simulated IO Error"):
            ActivityService.create_study_session(
                db=db_session,
                user_id="usr-tx-2",
                session_in=session_in,
            )

    sessions = list(db_session.scalars(select(StudySession).where(StudySession.user_id == "usr-tx-2")).all())
    assert len(sessions) == 0


# ==============================================================================
# TASK 2 & 4: RECOMMENDATION GENERATION & HUB INTEGRATION TESTS
# ==============================================================================

def test_recommendations_hub_structure_and_counts(db_session):
    """Verifies recommendations hub grouped structure, 4-element counts, and pending count."""
    user = User(id="usr-hub-1", email="hub1@test.com", hashed_password="pw", full_name="Hub User")
    subj = Subject(id="sub-hub-1", user_id="usr-hub-1", name="CS", code="CS1")
    top1 = Topic(id="top-hub-1", subject_id="sub-hub-1", name="Trees")
    top2 = Topic(id="top-hub-2", subject_id="sub-hub-1", name="Graphs")
    db_session.add_all([user, subj, top1, top2])
    db_session.commit()

    # Create recommendations across different elements and statuses
    r_perf = Recommendation(
        user_id="usr-hub-1", subject_id="sub-hub-1", topic_id="top-hub-1",
        agent_element="Performance Element", type="retention_decay", priority="high",
        title="Review Trees", reason_type="decay", reason_detail="detail", status="pending"
    )
    r_critic = Recommendation(
        user_id="usr-hub-1", subject_id="sub-hub-1", topic_id="top-hub-2",
        agent_element="Critic", type="pacing_optimization", priority="urgent",
        title="Remedial Graphs", reason_type="critic", reason_detail="detail", status="pending"
    )
    r_history = Recommendation(
        user_id="usr-hub-1", subject_id="sub-hub-1", topic_id="top-hub-1",
        agent_element="Learning Element", type="pacing_optimization", priority="low",
        title="Interval Expansion", reason_type="spaced_rep", reason_detail="detail", status="accepted"
    )
    db_session.add_all([r_perf, r_critic, r_history])
    db_session.commit()

    hub_data = RecommendationService.get_recommendations_hub(db_session, user_id="usr-hub-1")

    assert "activeRecommendations" in hub_data
    assert "history" in hub_data
    assert "countsByElement" in hub_data
    assert "totalPending" in hub_data

    assert len(hub_data["activeRecommendations"]) == 2
    assert len(hub_data["history"]) == 1
    assert hub_data["totalPending"] == 2

    counts = hub_data["countsByElement"]
    assert counts["Performance Element"] == 1
    assert counts["Critic"] == 1
    assert counts["Learning Element"] == 0
    assert counts["Problem Generator"] == 0


def test_recommendations_hub_empty_state_and_isolation(db_session):
    """Verifies clean empty state and multi-tenant isolation."""
    user_a = User(id="usr-a", email="a@hub.com", hashed_password="pw", full_name="User A")
    user_b = User(id="usr-b", email="b@hub.com", hashed_password="pw", full_name="User B")
    db_session.add_all([user_a, user_b])
    db_session.commit()

    # User B has a recommendation
    r_b = Recommendation(
        user_id="usr-b", agent_element="Performance Element", type="retention_decay",
        priority="high", title="User B Task", reason_type="decay", reason_detail="detail", status="pending"
    )
    db_session.add(r_b)
    db_session.commit()

    # User A has no recommendations
    hub_a = RecommendationService.get_recommendations_hub(db_session, user_id="usr-a")
    assert hub_a["totalPending"] == 0
    assert len(hub_a["activeRecommendations"]) == 0
    assert len(hub_a["history"]) == 0
    assert hub_a["countsByElement"]["Performance Element"] == 0


def test_explicit_recommendation_generation_and_deduplication(db_session):
    """Verifies that generate_fresh_recommendations persists new candidates without duplicate pending entries."""
    user = User(id="usr-gen-1", email="gen@test.com", hashed_password="pw", full_name="Gen User")
    subj = Subject(id="sub-gen-1", user_id="usr-gen-1", name="AI", code="AI1")
    top1 = Topic(id="top-gen-1", subject_id="sub-gen-1", name="Neural Nets", mastery_score=40.0, retention_score=35.0, decay_rate_lambda=0.10)
    db_session.add_all([user, subj, top1])
    db_session.commit()

    # First generation
    generated_1 = RecommendationService.generate_fresh_recommendations(db_session, user_id="usr-gen-1", max_recommendations=3)
    assert len(generated_1) >= 1

    # Second immediate generation should detect existing pending recommendation for top-gen-1 and avoid duplicate
    generated_2 = RecommendationService.generate_fresh_recommendations(db_session, user_id="usr-gen-1", max_recommendations=3)
    # Since topic is already pending, no duplicate is added
    assert len(generated_2) == 0

    # Total pending recommendations in DB should remain len(generated_1)
    pending_in_db = list(db_session.scalars(select(Recommendation).where(Recommendation.user_id == "usr-gen-1", Recommendation.status == "pending")).all())
    assert len(pending_in_db) == len(generated_1)
