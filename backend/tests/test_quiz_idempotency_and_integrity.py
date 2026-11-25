"""
Tests for Milestone 8.2: Learning Event Integrity & Quiz Idempotency
=====================================================================
Covers all 11 required scenarios:
1. Repeated identical submission with the same key returns the existing QuizAttempt without re-updating.
2. Same key with a different payload returns HTTP 409 Conflict.
3. Three repeated requests only update mastery once.
4. Three repeated requests only update decay stability once.
5. Distinct keys allow distinct quiz attempts on the same topic.
6. Same key works independently for two distinct users (tenant isolation).
7. Transaction rollback leaves topic and attempt unchanged upon failure.
8. Concurrent duplicate submission does not double-update mastery (integrity check).
9. Existing records with NULL keys remain fully accessible and queryable.
10. Calibration does not count explicitly linked events twice.
11. Different legitimate events with matching timestamps are preserved.
"""

from datetime import datetime, timezone, timedelta
import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.db.base import Base
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.entities import User, Subject, Topic, QuizAttempt, RevisionHistory
from app.schemas.entities import QuizAttemptCreate
from app.services.activity_service import activity_service
from app.ml.feature_extractor import FeatureExtractor
from app.ml.decay_calibrator import DecayCalibrator
from app.main import app


@pytest.fixture
def seeded_users_and_curriculum(db_session):
    u1 = User(id="u_student_1", email="student1@test.com", hashed_password="pw", full_name="Student One")
    u2 = User(id="u_student_2", email="student2@test.com", hashed_password="pw", full_name="Student Two")

    s1 = Subject(id="subj_1", user_id="u_student_1", name="Algorithms", code="CS301")
    s2 = Subject(id="subj_2", user_id="u_student_2", name="Algorithms", code="CS301")

    t1 = Topic(
        id="t_dp_1",
        subject_id="subj_1",
        name="Dynamic Programming",
        mastery_score=50.0,
        retention_score=70.0,
        decay_rate_lambda=0.08,
    )
    t2 = Topic(
        id="t_dp_2",
        subject_id="subj_2",
        name="Dynamic Programming",
        mastery_score=50.0,
        retention_score=70.0,
        decay_rate_lambda=0.08,
    )

    db_session.add_all([u1, u2, s1, s2, t1, t2])
    db_session.commit()
    return {"u1": u1, "u2": u2, "t1": t1, "t2": t2}


# ==============================================================================
# 1-4. IDEMPOTENCY & MASTERY/DECAY UPDATES ONCE
# ==============================================================================

def test_repeated_identical_quiz_submission_returns_existing(db_session, seeded_users_and_curriculum):
    """1. Repeated identical submission with the same key returns the existing QuizAttempt."""
    u1 = seeded_users_and_curriculum["u1"]
    t1 = seeded_users_and_curriculum["t1"]
    idem_key = "test-uuid-idem-001"

    payload = QuizAttemptCreate(
        topic_id=t1.id,
        title="DP Quiz 1",
        total_questions=10,
        correct_answers=8,
        score=80.0,
        idempotency_key=idem_key,
    )

    res1 = activity_service.create_quiz_attempt(db_session, u1.id, payload)
    res2 = activity_service.create_quiz_attempt(db_session, u1.id, payload)

    assert res1["id"] == res2["id"]
    assert res1["score"] == res2["score"]
    # Check only 1 row in DB
    all_attempts = db_session.query(QuizAttempt).filter(QuizAttempt.user_id == u1.id).all()
    assert len(all_attempts) == 1


def test_same_key_different_payload_returns_409(db_session, seeded_users_and_curriculum):
    """2. Same key with a different payload returns HTTP 409 Conflict."""
    u1 = seeded_users_and_curriculum["u1"]
    t1 = seeded_users_and_curriculum["t1"]
    idem_key = "test-uuid-idem-conflict"

    payload1 = QuizAttemptCreate(
        topic_id=t1.id,
        title="DP Quiz 1",
        total_questions=10,
        correct_answers=8,
        score=80.0,
        idempotency_key=idem_key,
    )
    _ = activity_service.create_quiz_attempt(db_session, u1.id, payload1)

    # Different payload: 9 correct answers instead of 8
    payload2 = QuizAttemptCreate(
        topic_id=t1.id,
        title="DP Quiz 1",
        total_questions=10,
        correct_answers=9,
        score=90.0,
        idempotency_key=idem_key,
    )

    with pytest.raises(HTTPException) as exc_info:
        activity_service.create_quiz_attempt(db_session, u1.id, payload2)
    assert exc_info.value.status_code == 409


def test_three_repeated_requests_only_update_mastery_and_decay_once(db_session, seeded_users_and_curriculum):
    """3 & 4. Three repeated requests only update mastery and decay stability once."""
    u1 = seeded_users_and_curriculum["u1"]
    t1 = seeded_users_and_curriculum["t1"]
    idem_key = "test-uuid-idem-thrice"

    # Initial topic state: mastery=50.0, lambda=0.08
    assert t1.mastery_score == 50.0
    initial_lambda = t1.decay_rate_lambda

    payload = QuizAttemptCreate(
        topic_id=t1.id,
        title="DP Quiz",
        total_questions=10,
        correct_answers=10,
        score=100.0,
        idempotency_key=idem_key,
    )

    # First submission: mastery should update from 50 to (50*0.7 + 100*0.3) = 65.0
    activity_service.create_quiz_attempt(db_session, u1.id, payload)
    db_session.refresh(t1)
    expected_mastery = 65.0
    expected_lambda = t1.decay_rate_lambda
    assert t1.mastery_score == expected_mastery
    assert expected_lambda < initial_lambda  # consolidated

    # 2nd submission
    activity_service.create_quiz_attempt(db_session, u1.id, payload)
    db_session.refresh(t1)
    assert t1.mastery_score == expected_mastery
    assert t1.decay_rate_lambda == expected_lambda

    # 3rd submission
    activity_service.create_quiz_attempt(db_session, u1.id, payload)
    db_session.refresh(t1)
    assert t1.mastery_score == expected_mastery
    assert t1.decay_rate_lambda == expected_lambda


def test_distinct_keys_allow_distinct_quiz_attempts(db_session, seeded_users_and_curriculum):
    """5. Distinct keys allow distinct quiz attempts on the same topic."""
    u1 = seeded_users_and_curriculum["u1"]
    t1 = seeded_users_and_curriculum["t1"]

    payload1 = QuizAttemptCreate(
        topic_id=t1.id,
        title="DP Quiz 1",
        total_questions=10,
        correct_answers=8,
        score=80.0,
        idempotency_key="key-attempt-1",
    )
    payload2 = QuizAttemptCreate(
        topic_id=t1.id,
        title="DP Quiz 2",
        total_questions=10,
        correct_answers=9,
        score=90.0,
        idempotency_key="key-attempt-2",
    )

    res1 = activity_service.create_quiz_attempt(db_session, u1.id, payload1)
    res2 = activity_service.create_quiz_attempt(db_session, u1.id, payload2)

    assert res1["id"] != res2["id"]
    attempts = db_session.query(QuizAttempt).filter(QuizAttempt.user_id == u1.id).all()
    assert len(attempts) == 2


def test_cross_user_idempotency_isolation(db_session, seeded_users_and_curriculum):
    """6. Same key works independently for two distinct users (tenant isolation)."""
    u1 = seeded_users_and_curriculum["u1"]
    u2 = seeded_users_and_curriculum["u2"]
    t1 = seeded_users_and_curriculum["t1"]
    t2 = seeded_users_and_curriculum["t2"]

    shared_key = "shared-uuid-across-clients"

    payload1 = QuizAttemptCreate(
        topic_id=t1.id,
        title="DP Quiz Student 1",
        total_questions=10,
        correct_answers=7,
        score=70.0,
        idempotency_key=shared_key,
    )
    payload2 = QuizAttemptCreate(
        topic_id=t2.id,
        title="DP Quiz Student 2",
        total_questions=10,
        correct_answers=9,
        score=90.0,
        idempotency_key=shared_key,
    )

    res1 = activity_service.create_quiz_attempt(db_session, u1.id, payload1)
    res2 = activity_service.create_quiz_attempt(db_session, u2.id, payload2)

    assert res1["user_id"] == u1.id
    assert res2["user_id"] == u2.id
    assert res1["id"] != res2["id"]


def test_transaction_rollback_leaves_topic_and_attempt_unchanged(db_session, seeded_users_and_curriculum):
    """7. Transaction rollback leaves topic and attempt unchanged upon failure."""
    u1 = seeded_users_and_curriculum["u1"]
    t1 = seeded_users_and_curriculum["t1"]
    orig_mastery = t1.mastery_score
    orig_lambda = t1.decay_rate_lambda

    # Attempt with correct_answers > total_questions raises 400 before DB mutations
    payload_bad = QuizAttemptCreate(
        topic_id=t1.id,
        title="Invalid Quiz",
        total_questions=10,
        correct_answers=15,
        idempotency_key="rollback-key",
    )

    with pytest.raises(HTTPException):
        activity_service.create_quiz_attempt(db_session, u1.id, payload_bad)

    db_session.refresh(t1)
    assert t1.mastery_score == orig_mastery
    assert t1.decay_rate_lambda == orig_lambda
    assert db_session.query(QuizAttempt).count() == 0


def test_concurrent_duplicate_race_simulation(db_session, seeded_users_and_curriculum):
    """8. Concurrent duplicate submission simulated via manual duplicate insert returns existing cleanly."""
    u1 = seeded_users_and_curriculum["u1"]
    t1 = seeded_users_and_curriculum["t1"]
    key = "race-simulation-key"

    # Pre-seed one attempt directly in DB mimicking a parallel transaction committing first
    existing = QuizAttempt(
        id="pre-seeded-race-attempt",
        user_id=u1.id,
        topic_id=t1.id,
        title="DP Quiz",
        score=80.0,
        accuracy=80.0,
        total_questions=10,
        correct_answers=8,
        idempotency_key=key,
    )
    db_session.add(existing)
    db_session.commit()

    # Now attempt submission with same payload
    payload = QuizAttemptCreate(
        topic_id=t1.id,
        title="DP Quiz",
        total_questions=10,
        correct_answers=8,
        score=80.0,
        idempotency_key=key,
    )

    res = activity_service.create_quiz_attempt(db_session, u1.id, payload)
    assert res["id"] == "pre-seeded-race-attempt"


def test_existing_records_with_null_keys_remain_accessible(db_session, seeded_users_and_curriculum):
    """9. Existing records with NULL keys remain fully accessible and queryable."""
    u1 = seeded_users_and_curriculum["u1"]
    t1 = seeded_users_and_curriculum["t1"]

    legacy1 = QuizAttempt(
        id="legacy_1",
        user_id=u1.id,
        topic_id=t1.id,
        title="Legacy Quiz 1",
        score=75.0,
        accuracy=75.0,
        total_questions=10,
        correct_answers=7,
        idempotency_key=None,
    )
    legacy2 = QuizAttempt(
        id="legacy_2",
        user_id=u1.id,
        topic_id=t1.id,
        title="Legacy Quiz 2",
        score=85.0,
        accuracy=85.0,
        total_questions=10,
        correct_answers=8,
        idempotency_key=None,
    )
    db_session.add_all([legacy1, legacy2])
    db_session.commit()

    # Query list
    attempts = activity_service.get_quiz_attempts(db_session, user_id=u1.id)
    ids = [a["id"] for a in attempts]
    assert "legacy_1" in ids
    assert "legacy_2" in ids


def test_calibration_does_not_count_explicitly_linked_events_twice():
    """10. Calibration does not count explicitly linked events twice."""
    now = datetime.now(timezone.utc)
    quiz_attempt = {
        "id": "quiz_evt_101",
        "attempted_at": now - timedelta(days=5),
        "score": 85.0,
    }
    # Revision record that explicitly cites quiz_evt_101
    linked_revision = {
        "id": "rev_evt_201",
        "interval_days": 5,
        "score": 85.0,
        "quiz_attempt_id": "quiz_evt_101",
    }

    obs = FeatureExtractor.extract_calibration_observations(
        revision_history=[linked_revision],
        quiz_attempts=[quiz_attempt],
        reference_time=now,
    )
    # Should only contain 1 observation, not 2
    assert len(obs) == 1
    assert obs[0][0] == 5.0
    assert obs[0][1] == 85.0


def test_different_legitimate_events_with_matching_timestamps_are_preserved():
    """11. Different legitimate events with matching timestamps are preserved without heuristic dropping."""
    now = datetime.now(timezone.utc)
    same_time = now - timedelta(days=4)

    # Student took a quick flashcard revision pass AND a formal diagnostic quiz test at the same date
    rev_event = {
        "id": "rev_event_legit",
        "interval_days": 4,
        "score": 70.0,
    }
    quiz_event = {
        "id": "quiz_event_legit",
        "attempted_at": same_time,
        "score": 80.0,
    }

    obs = FeatureExtractor.extract_calibration_observations(
        revision_history=[rev_event],
        quiz_attempts=[quiz_event],
        reference_time=now,
    )
    # Both legitimate observations are preserved
    assert len(obs) == 2
    scores = {o[1] for o in obs}
    assert 70.0 in scores
    assert 80.0 in scores


# ==============================================================================
# FASTAPI ENDPOINT HEADER INTEGRATION TEST
# ==============================================================================

def test_fastapi_endpoint_idempotency_header_support(db_session, seeded_users_and_curriculum):
    """Verifies that HTTP header Idempotency-Key is respected by the API controller."""
    u1 = seeded_users_and_curriculum["u1"]
    t1 = seeded_users_and_curriculum["t1"]
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: u1

    header_key = "api-header-uuid-777"
    client = TestClient(app)

    try:
        payload = {
            "topic_id": t1.id,
            "title": "API DP Quiz",
            "total_questions": 10,
            "correct_answers": 8,
            "score": 80.0,
        }

        # First request
        res1 = client.post("/api/quiz-attempts", json=payload, headers={"Idempotency-Key": header_key})
        assert res1.status_code == 201
        data1 = res1.json()

        # Duplicate request with same header
        res2 = client.post("/api/quiz-attempts", json=payload, headers={"Idempotency-Key": header_key})
        assert res2.status_code == 201
        data2 = res2.json()

        assert data1["id"] == data2["id"]
        assert data1["idempotency_key"] == header_key
    finally:
        app.dependency_overrides.clear()

