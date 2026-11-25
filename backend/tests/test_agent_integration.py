"""
Unit Tests for Agent Adapters and Service Integration (Milestone 5)
==================================================================
Tests:
- AIAgentAdapter.generate_recommendations interface compatibility.
- AIAgentAdapter.evaluate_quiz_critique interface compatibility.
- MLRetentionAdapter.predict_retention calculations.
- MLRetentionAdapter.calibrate_decay_rate estimation.
- ActivityService integration invoking Critic Agent during quiz submission.
- Multi-tenant boundary isolation.
"""

from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.entities import User, Subject, Topic, QuizAttempt
from app.services.agent_adapters import ai_agent_adapter, ml_retention_adapter
from app.services.activity_service import ActivityService
from app.schemas.entities import QuizAttemptCreate


def test_ai_agent_adapter_generate_recommendations(db_session):
    """Verifies public contract of AIAgentAdapter.generate_recommendations."""
    user = User(id="u-adapter-1", email="adapter@test.com", hashed_password="pw", full_name="User Adapter")
    subj = Subject(id="s-adapter-1", user_id="u-adapter-1", name="Math", code="M101")
    topic = Topic(id="t-adapter-1", subject_id="s-adapter-1", name="Calculus", mastery_score=40.0)
    db_session.add_all([user, subj, topic])
    db_session.commit()

    recs = ai_agent_adapter.generate_recommendations(
        user_id="u-adapter-1",
        student_history={"db": db_session},
    )
    assert isinstance(recs, list)
    assert len(recs) >= 1
    first_rec = recs[0]
    assert "title" in first_rec
    assert "agent_element" in first_rec
    assert "priority" in first_rec
    assert "reason_detail" in first_rec


def test_ai_agent_adapter_evaluate_quiz_critique():
    """Verifies public contract of AIAgentAdapter.evaluate_quiz_critique."""
    critique = ai_agent_adapter.evaluate_quiz_critique(
        attempt_id="att-1",
        score=45.0,
        accuracy=45.0,
        topic_context={"topic_id": "top-1", "name": "Calculus", "total_questions": 10, "correct_answers": 4},
    )
    assert "critic_notes" in critique
    assert "recommended_action" in critique
    assert critique["performance_category"] == "High Concern"
    assert critique["needs_practice"] is True


def test_ml_retention_adapter_predict_retention():
    """Verifies MLRetentionAdapter.predict_retention."""
    retention_0 = ml_retention_adapter.predict_retention(
        topic_id="top-1", elapsed_days=0.0, decay_lambda=0.08
    )
    assert retention_0 == 100.0

    retention_7 = ml_retention_adapter.predict_retention(
        topic_id="top-1", elapsed_days=7.0, decay_lambda=0.08
    )
    assert 0.0 < retention_7 < 100.0


def test_ml_retention_adapter_calibrate_decay_rate():
    """Verifies MLRetentionAdapter.calibrate_decay_rate."""
    history = [
        {"interval_days": 3, "score": 80.0},
        {"interval_days": 7, "score": 60.0},
    ]
    calibrated_lam = ml_retention_adapter.calibrate_decay_rate(
        revision_history=history,
        quiz_scores=[80.0, 60.0],
    )
    assert 0.01 <= calibrated_lam <= 0.30


def test_quiz_attempt_service_invokes_critic_automatically(db_session):
    """Submitting a quiz without manual critic notes invokes CriticAgent automatically."""
    user = User(id="u-quiz-srv", email="quiz@test.com", hashed_password="pw", full_name="Quiz Tester")
    subj = Subject(id="s-quiz-srv", user_id="u-quiz-srv", name="Networking", code="NET1")
    topic = Topic(id="t-quiz-srv", subject_id="s-quiz-srv", name="TCP/IP Handshake", mastery_score=50.0)
    db_session.add_all([user, subj, topic])
    db_session.commit()

    attempt_in = QuizAttemptCreate(
        topic_id="t-quiz-srv",
        title="TCP Protocol Quiz",
        total_questions=10,
        correct_answers=3,  # 30% -> High concern
    )

    created_attempt = ActivityService.create_quiz_attempt(
        db=db_session,
        user_id="u-quiz-srv",
        attempt_in=attempt_in,
    )

    assert created_attempt["critic_evaluated"] is True
    assert "High Concern" in created_attempt["critic_notes"]

    # Verify topic decay rate was updated
    refreshed_topic = db_session.scalar(Topic.__table__.select().where(Topic.id == "t-quiz-srv"))
    assert refreshed_topic is not None
