"""
Unit Tests for Student Context Builder
"""

from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.entities import User, Subject, Topic, QuizAttempt, StudySession, Recommendation
from app.agents.context import StudentContextBuilder


def test_student_context_builder_empty_history(db_session):
    """Handles user with zero subjects, zero topics, and zero quizzes safely."""
    user = User(
        id="usr-test-1",
        email="student@neurolearn.test",
        hashed_password="pw",
        full_name="Alice Student",
    )
    db_session.add(user)
    db_session.commit()

    context = StudentContextBuilder.build_from_db(db_session, user_id="usr-test-1")
    assert context is not None
    assert context.student.user_id == "usr-test-1"
    assert context.student.full_name == "Alice Student"
    assert len(context.subjects) == 0
    assert len(context.topics) == 0
    assert len(context.recent_quizzes) == 0
    assert len(context.study_sessions) == 0


def test_student_context_builder_with_entities_and_isolation(db_session):
    """Verifies complete entity assembly and multi-tenant isolation."""
    # User A
    user_a = User(id="user-a", email="a@test.com", hashed_password="pw", full_name="User A")
    # User B
    user_b = User(id="user-b", email="b@test.com", hashed_password="pw", full_name="User B")
    db_session.add_all([user_a, user_b])
    db_session.commit()

    ref_time = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)
    exam_time = ref_time + timedelta(days=10)

    # User A Subject & Topic
    subj_a = Subject(id="sub-a", user_id="user-a", name="Math", code="MATH1", exam_date=exam_time)
    db_session.add(subj_a)
    db_session.commit()

    topic_a = Topic(
        id="top-a",
        subject_id="sub-a",
        name="Linear Algebra",
        mastery_score=60.0,
        retention_score=75.0,
        last_revised=ref_time - timedelta(days=4),
    )
    # User B Subject & Topic
    subj_b = Subject(id="sub-b", user_id="user-b", name="Physics", code="PHYS1")
    db_session.add_all([topic_a, subj_b])
    db_session.commit()

    topic_b = Topic(id="top-b", subject_id="sub-b", name="Kinematics")
    db_session.add(topic_b)
    db_session.commit()

    # Context for User A
    ctx_a = StudentContextBuilder.build_from_db(db_session, "user-a", reference_time=ref_time)
    assert ctx_a is not None
    assert len(ctx_a.subjects) == 1
    assert ctx_a.subjects[0].name == "Math"
    assert ctx_a.subjects[0].days_until_exam == pytest.approx(10.0, rel=1e-2)
    assert len(ctx_a.topics) == 1
    assert ctx_a.topics[0].name == "Linear Algebra"
    assert ctx_a.topics[0].elapsed_days == pytest.approx(4.0, rel=1e-2)

    # Ensure User B's entities are never leaked into User A's context
    subject_ids = [s.id for s in ctx_a.subjects]
    assert "sub-b" not in subject_ids
    topic_ids = [t.id for t in ctx_a.topics]
    assert "top-b" not in topic_ids


def test_student_context_nonexistent_user(db_session):
    """Returns None for non-existent user ID."""
    ctx = StudentContextBuilder.build_from_db(db_session, "nonexistent-id")
    assert ctx is None
