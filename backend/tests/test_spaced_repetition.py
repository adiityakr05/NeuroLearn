"""
Unit and Integration Tests for Spaced Repetition Endpoint & Queue
==================================================================
Tests:
1. Authenticated request returns 200 and schema matches.
2. Unauthenticated request returns 401 Unauthorized.
3. Student ownership isolation (User A cannot see User B's topics).
4. Topics due for revision (urgency critical / warning).
5. Topics approaching revision (optimal / retained).
6. Empty topic list returns empty array cleanly.
7. Missing revision dates (last_revised=None, next_revision=None).
8. Invalid or future dates handled gracefully without NaN or error.
9. Retention ordering: highest urgency / lowest retention first.
10. Read-only behavior: GET does not modify Topic mastery or decay rates.
"""

from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.entities import User, Subject, Topic, RevisionHistory
from app.services.planner_service import planner_service
from app.main import app


@pytest.fixture
def test_db(db_session):
    return db_session


@pytest.fixture
def sample_users_and_topics(test_db):
    user_a = User(id="user_sr_a", email="student_a@neurolearn.ai", hashed_password="pw", full_name="Student A")
    user_b = User(id="user_sr_b", email="student_b@neurolearn.ai", hashed_password="pw", full_name="Student B")

    subj_a1 = Subject(id="subj_a1", user_id="user_sr_a", name="Computer Science", code="CS101")
    subj_b1 = Subject(id="subj_b1", user_id="user_sr_b", name="Mathematics", code="MATH101")

    now = datetime.now(timezone.utc)

    # Topic 1: Overdue topic (last revised 10 days ago, lambda=0.15) -> Critical
    topic_critical = Topic(
        id="t_critical",
        subject_id="subj_a1",
        name="Dynamic Programming",
        difficulty="Hard",
        mastery_score=45.0,
        retention_score=70.0,
        decay_rate_lambda=0.15,
        last_revised=now - timedelta(days=10),
        next_revision=now - timedelta(days=2),
    )

    # Topic 2: Approaching revision (last revised 2 days ago, lambda=0.08) -> Warning / Optimal
    topic_warning = Topic(
        id="t_warning",
        subject_id="subj_a1",
        name="Binary Search Trees",
        difficulty="Medium",
        mastery_score=65.0,
        retention_score=85.0,
        decay_rate_lambda=0.08,
        last_revised=now - timedelta(days=2),
        next_revision=now + timedelta(days=1),
    )

    # Topic 3: Well retained (studied 1 hour ago) -> Retained
    topic_retained = Topic(
        id="t_retained",
        subject_id="subj_a1",
        name="Arrays and Strings",
        difficulty="Easy",
        mastery_score=90.0,
        retention_score=98.0,
        decay_rate_lambda=0.04,
        last_revised=now - timedelta(hours=2),
        next_revision=now + timedelta(days=14),
    )

    # Topic for User B
    topic_b = Topic(
        id="t_user_b",
        subject_id="subj_b1",
        name="Linear Algebra",
        difficulty="Hard",
        mastery_score=50.0,
        retention_score=60.0,
        decay_rate_lambda=0.10,
        last_revised=now - timedelta(days=5),
    )

    test_db.add_all([user_a, user_b, subj_a1, subj_b1, topic_critical, topic_warning, topic_retained, topic_b])
    test_db.commit()

    return {"user_a": user_a, "user_b": user_b, "topics": [topic_critical, topic_warning, topic_retained, topic_b]}


def test_unauthenticated_request():
    """Requirement 2: Unauthenticated request must return 401."""
    client = TestClient(app)
    response = client.get("/api/spaced-repetition")
    assert response.status_code == 401


def test_authenticated_request_structure(test_db, sample_users_and_topics):
    """Requirement 1: Authenticated request returns 200 and matches frontend expected structure."""
    user_a = sample_users_and_topics["user_a"]

    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_current_user] = lambda: user_a

    try:
        client = TestClient(app)
        response = client.get("/api/spaced-repetition")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3  # Only user_a's 3 topics

        first = data[0]
        # Frontend SpacedRepetitionSidebar required keys:
        assert "id" in first
        assert "topic" in first
        assert "subject" in first
        assert "daysSinceReview" in first
        assert "estimatedRetention" in first
        assert "urgency" in first
        assert "repetitionStage" in first
        assert "examWeight" in first
        assert "scheduledDate" in first
    finally:
        app.dependency_overrides.clear()


def test_student_ownership_isolation(test_db, sample_users_and_topics):
    """Requirement 3: Student ownership isolation."""
    user_b = sample_users_and_topics["user_b"]

    queue_b = planner_service.get_spaced_repetition_queue(test_db, user_b.id)
    assert len(queue_b) == 1
    assert queue_b[0]["topic"] == "Linear Algebra"
    assert queue_b[0]["subject"] == "Mathematics"

    # User B should NOT see User A's topics
    topic_names = [item["topic"] for item in queue_b]
    assert "Dynamic Programming" not in topic_names
    assert "Arrays and Strings" not in topic_names


def test_topics_due_and_approaching_revision(test_db, sample_users_and_topics):
    """Requirements 4 & 5: Topics due vs approaching revision categorized properly."""
    user_a = sample_users_and_topics["user_a"]
    queue = planner_service.get_spaced_repetition_queue(test_db, user_a.id)

    by_topic = {item["topic"]: item for item in queue}

    # Overdue topic should be critical
    dp = by_topic["Dynamic Programming"]
    assert dp["urgency"] == "critical"
    assert "Overdue" in dp["repetitionStage"]

    # Retained topic
    arrays = by_topic["Arrays and Strings"]
    assert arrays["urgency"] == "retained"
    assert "Retained" in arrays["repetitionStage"]
    assert arrays["estimatedRetention"] > 90.0


def test_empty_topic_list(test_db):
    """Requirement 6: Empty topic list returns empty array cleanly."""
    user_empty = User(id="user_empty", email="empty@neurolearn.ai", hashed_password="pw", full_name="Empty Student")
    test_db.add(user_empty)
    test_db.commit()

    queue = planner_service.get_spaced_repetition_queue(test_db, user_empty.id)
    assert queue == []


def test_missing_revision_dates(test_db):
    """Requirement 7: Missing revision dates (last_revised=None, next_revision=None)."""
    user = User(id="user_missing_dt", email="missing@neurolearn.ai", hashed_password="pw", full_name="Missing Dates")
    subj = Subject(id="subj_missing_dt", user_id="user_missing_dt", name="Physics", code="PHY101")
    topic = Topic(
        id="t_missing_dt",
        subject_id="subj_missing_dt",
        name="Quantum Mechanics",
        difficulty="Hard",
        decay_rate_lambda=0.08,
        last_revised=None,
        next_revision=None,
    )
    test_db.add_all([user, subj, topic])
    test_db.commit()

    queue = planner_service.get_spaced_repetition_queue(test_db, user.id)
    assert len(queue) == 1
    item = queue[0]
    assert item["topic"] == "Quantum Mechanics"
    assert item["daysSinceReview"] >= 0.0
    assert 0.0 <= item["estimatedRetention"] <= 100.0
    assert item["scheduledDate"] is not None


def test_invalid_or_future_dates(test_db):
    """Requirement 8: Future dates or zero days handled safely without NaN or negative elapsed days."""
    user = User(id="user_future_dt", email="future@neurolearn.ai", hashed_password="pw", full_name="Future Student")
    subj = Subject(id="subj_future_dt", user_id="user_future_dt", name="Chemistry", code="CHEM101")
    now = datetime.now(timezone.utc)
    topic = Topic(
        id="t_future_dt",
        subject_id="subj_future_dt",
        name="Organic Synthesis",
        difficulty="Medium",
        decay_rate_lambda=0.08,
        last_revised=now + timedelta(days=5),  # Future date
        next_revision=now + timedelta(days=10),
    )
    test_db.add_all([user, subj, topic])
    test_db.commit()

    queue = planner_service.get_spaced_repetition_queue(test_db, user.id)
    assert len(queue) == 1
    item = queue[0]
    # Elapsed days must not be negative
    assert item["daysSinceReview"] == 0.0
    assert item["estimatedRetention"] == 100.0


def test_retention_ordering(test_db, sample_users_and_topics):
    """Requirement 9: Ordered by urgency rank (critical first) then lowest retention."""
    user_a = sample_users_and_topics["user_a"]
    queue = planner_service.get_spaced_repetition_queue(test_db, user_a.id)

    # First item must be the critical topic
    assert queue[0]["topic"] == "Dynamic Programming"
    assert queue[0]["urgency"] == "critical"

    # Last item must be the retained topic
    assert queue[-1]["topic"] == "Arrays and Strings"
    assert queue[-1]["urgency"] == "retained"


def test_read_only_behavior(test_db, sample_users_and_topics):
    """Requirement 10: GET call must not modify topic mastery, retention, or decay rates in DB."""
    topic = test_db.query(Topic).filter(Topic.id == "t_critical").first()
    orig_mastery = topic.mastery_score
    orig_retention = topic.retention_score
    orig_lambda = topic.decay_rate_lambda
    orig_updated_at = topic.updated_at

    user_a = sample_users_and_topics["user_a"]
    _ = planner_service.get_spaced_repetition_queue(test_db, user_a.id)

    refreshed_topic = test_db.query(Topic).filter(Topic.id == "t_critical").first()
    assert refreshed_topic.mastery_score == orig_mastery
    assert refreshed_topic.retention_score == orig_retention
    assert refreshed_topic.decay_rate_lambda == orig_lambda
    assert refreshed_topic.updated_at == orig_updated_at
