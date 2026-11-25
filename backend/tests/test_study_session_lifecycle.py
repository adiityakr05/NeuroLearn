import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.db.base import Base
from app.main import app
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.entities import User, Subject, Topic, StudySession
from app.schemas.entities import StudySessionCreate, StudySessionUpdate
from app.services.activity_service import activity_service
from app.services.planner_service import planner_service


@pytest.fixture
def seeded_users_and_subjects(db_session):
    """Creates two isolated test students and subjects."""
    db_session.query(StudySession).delete()
    db_session.query(Topic).delete()
    db_session.query(Subject).delete()
    db_session.query(User).delete()
    db_session.commit()

    u1 = User(
        id="u_session_student_1",
        email="student1_session@test.com",
        full_name="Student One",
        hashed_password="pw",
    )
    u2 = User(
        id="u_session_student_2",
        email="student2_session@test.com",
        full_name="Student Two",
        hashed_password="pw",
    )
    db_session.add_all([u1, u2])
    db_session.commit()

    sub1 = Subject(
        id="sub_algo_1",
        user_id=u1.id,
        name="Algorithms",
        code="CS301",
    )
    sub2 = Subject(
        id="sub_algo_2",
        user_id=u2.id,
        name="Algorithms",
        code="CS301",
    )
    db_session.add_all([sub1, sub2])
    db_session.commit()

    t1 = Topic(
        id="top_dp_1",
        subject_id=sub1.id,
        name="Dynamic Programming",
        difficulty="Hard",
        mastery_score=50.0,
        decay_rate_lambda=0.08,
    )
    db_session.add(t1)
    db_session.commit()

    return {"u1": u1, "u2": u2, "sub1": sub1, "sub2": sub2, "t1": t1}


def test_1_create_pending_session(db_session, seeded_users_and_subjects):
    """1. Creating a pending session with planned duration and default pending status."""
    u1 = seeded_users_and_subjects["u1"]
    sub1 = seeded_users_and_subjects["sub1"]
    t1 = seeded_users_and_subjects["t1"]

    session_in = StudySessionCreate(
        subject_id=sub1.id,
        topic_id=t1.id,
        date="2026-11-26",
        duration_minutes=45,
        status="pending",
    )
    created = activity_service.create_study_session(db_session, u1.id, session_in)

    assert created["id"] is not None
    assert created["status"] == "pending"
    assert created["duration_minutes"] == 45
    assert created["actual_duration_minutes"] is None
    assert created["started_at"] is None
    assert created["completed_at"] is None


def test_2_start_pending_session(db_session, seeded_users_and_subjects):
    """2. Starting a pending session transitions to in_progress with started_at recorded."""
    u1 = seeded_users_and_subjects["u1"]
    sub1 = seeded_users_and_subjects["sub1"]

    session_in = StudySessionCreate(
        subject_id=sub1.id,
        date="2026-11-26",
        duration_minutes=60,
    )
    created = activity_service.create_study_session(db_session, u1.id, session_in)

    start_time = datetime.now(timezone.utc) - timedelta(minutes=30)
    started = activity_service.start_study_session(db_session, created["id"], u1.id, started_at=start_time)

    assert started["status"] == "in_progress"
    assert started["started_at"] is not None
    assert started["completed_at"] is None
    assert started["actual_duration_minutes"] is None


def test_3_complete_in_progress_session_and_calculate_duration(db_session, seeded_users_and_subjects):
    """3. Completing an in-progress session calculates actual duration from timestamps."""
    u1 = seeded_users_and_subjects["u1"]
    sub1 = seeded_users_and_subjects["sub1"]

    created = activity_service.create_study_session(
        db_session, u1.id, StudySessionCreate(subject_id=sub1.id, date="2026-11-26", duration_minutes=45)
    )
    start_time = datetime.now(timezone.utc) - timedelta(minutes=40)
    activity_service.start_study_session(db_session, created["id"], u1.id, started_at=start_time)

    completion_time = datetime.now(timezone.utc)
    completed = activity_service.complete_study_session(
        db_session, created["id"], u1.id, completed_at=completion_time
    )

    assert completed["status"] == "completed"
    assert completed["completed_at"] is not None
    assert completed["started_at"] is not None
    assert completed["actual_duration_minutes"] >= 39  # Approximately 40 mins
    assert completed["duration_minutes"] == 45  # Planned duration unchanged!


def test_4_abandon_in_progress_session(db_session, seeded_users_and_subjects):
    """4. Abandoning an in-progress session records duration without marking completed."""
    u1 = seeded_users_and_subjects["u1"]
    sub1 = seeded_users_and_subjects["sub1"]

    created = activity_service.create_study_session(
        db_session, u1.id, StudySessionCreate(subject_id=sub1.id, date="2026-11-26", duration_minutes=60)
    )
    activity_service.start_study_session(db_session, created["id"], u1.id)

    abandoned = activity_service.abandon_study_session(
        db_session, created["id"], u1.id, actual_duration_minutes=20, reason="Interrupted by urgent meeting"
    )

    assert abandoned["status"] == "abandoned"
    assert abandoned["completed_at"] is None
    assert abandoned["actual_duration_minutes"] == 20
    assert abandoned["duration_minutes"] == 60
    assert "Interrupted by urgent meeting" in abandoned["ai_reason"]


def test_5_reject_invalid_state_transitions(db_session, seeded_users_and_subjects):
    """5. Reject invalid state transitions with appropriate HTTP errors."""
    u1 = seeded_users_and_subjects["u1"]
    sub1 = seeded_users_and_subjects["sub1"]

    # Session A: completed -> cannot start or abandon
    s_comp = activity_service.create_study_session(
        db_session, u1.id, StudySessionCreate(subject_id=sub1.id, date="2026-11-26", duration_minutes=30)
    )
    activity_service.complete_study_session(db_session, s_comp["id"], u1.id)

    # Cannot start an already completed session
    with pytest.raises(HTTPException) as exc_info:
        activity_service.start_study_session(db_session, s_comp["id"], u1.id)
    assert exc_info.value.status_code == 400

    # Cannot abandon an already completed session
    with pytest.raises(HTTPException) as exc_info:
        activity_service.abandon_study_session(db_session, s_comp["id"], u1.id)
    assert exc_info.value.status_code == 400

    # Cannot update status of an already completed session via update_study_session
    with pytest.raises(HTTPException) as exc_info:
        activity_service.update_study_session(
            db_session, s_comp["id"], u1.id, StudySessionUpdate(status="in_progress")
        )
    assert exc_info.value.status_code == 400


def test_6_prevent_duplicate_completion(db_session, seeded_users_and_subjects):
    """6. Completed sessions must not accidentally be completed twice."""
    u1 = seeded_users_and_subjects["u1"]
    sub1 = seeded_users_and_subjects["sub1"]

    session = activity_service.create_study_session(
        db_session, u1.id, StudySessionCreate(subject_id=sub1.id, date="2026-11-26", duration_minutes=30)
    )
    activity_service.complete_study_session(db_session, session["id"], u1.id, actual_duration_minutes=28)

    # Second completion attempt fails with 400
    with pytest.raises(HTTPException) as exc_info:
        activity_service.complete_study_session(db_session, session["id"], u1.id, actual_duration_minutes=35)
    assert exc_info.value.status_code == 400
    assert "already completed" in str(exc_info.value.detail).lower()

    # Via generic update endpoint
    with pytest.raises(HTTPException) as exc_info:
        activity_service.update_study_session(
            db_session, session["id"], u1.id, StudySessionUpdate(status="completed")
        )
    assert exc_info.value.status_code == 400


def test_7_user_reported_actual_duration(db_session, seeded_users_and_subjects):
    """7. User can explicitly report actual duration upon completion."""
    u1 = seeded_users_and_subjects["u1"]
    sub1 = seeded_users_and_subjects["sub1"]

    session = activity_service.create_study_session(
        db_session, u1.id, StudySessionCreate(subject_id=sub1.id, date="2026-11-26", duration_minutes=45)
    )
    completed = activity_service.complete_study_session(
        db_session, session["id"], u1.id, actual_duration_minutes=52
    )

    assert completed["status"] == "completed"
    assert completed["actual_duration_minutes"] == 52
    assert completed["duration_minutes"] == 45


def test_8_preserve_planned_duration(db_session, seeded_users_and_subjects):
    """8. Never overwrite planned duration with actual duration."""
    u1 = seeded_users_and_subjects["u1"]
    sub1 = seeded_users_and_subjects["sub1"]

    session = activity_service.create_study_session(
        db_session, u1.id, StudySessionCreate(subject_id=sub1.id, date="2026-11-26", duration_minutes=90)
    )
    activity_service.start_study_session(db_session, session["id"], u1.id)
    completed = activity_service.complete_study_session(
        db_session, session["id"], u1.id, actual_duration_minutes=15
    )

    assert completed["duration_minutes"] == 90
    assert completed["actual_duration_minutes"] == 15

    # Check database model directly
    db_obj = db_session.query(StudySession).filter_by(id=session["id"]).first()
    assert db_obj.duration_minutes == 90
    assert db_obj.actual_duration_minutes == 15


def test_9_reject_negative_or_invalid_durations(db_session, seeded_users_and_subjects):
    """9. Rejects negative or unreasonable durations."""
    u1 = seeded_users_and_subjects["u1"]
    sub1 = seeded_users_and_subjects["sub1"]

    session = activity_service.create_study_session(
        db_session, u1.id, StudySessionCreate(subject_id=sub1.id, date="2026-11-26", duration_minutes=45)
    )

    with pytest.raises(HTTPException) as exc_info:
        activity_service.complete_study_session(db_session, session["id"], u1.id, actual_duration_minutes=-10)
    assert exc_info.value.status_code == 400

    with pytest.raises(HTTPException) as exc_info:
        activity_service.complete_study_session(db_session, session["id"], u1.id, actual_duration_minutes=2000)
    assert exc_info.value.status_code == 400


def test_10_cross_user_session_isolation(db_session, seeded_users_and_subjects):
    """10. Cross-user session isolation: cannot start, complete, or modify another user's session."""
    u1 = seeded_users_and_subjects["u1"]
    u2 = seeded_users_and_subjects["u2"]
    sub1 = seeded_users_and_subjects["sub1"]

    s1 = activity_service.create_study_session(
        db_session, u1.id, StudySessionCreate(subject_id=sub1.id, date="2026-11-26", duration_minutes=45)
    )

    # u2 tries to read u1's session
    with pytest.raises(HTTPException) as exc_info:
        activity_service.get_study_session_by_id(db_session, s1["id"], u2.id)
    assert exc_info.value.status_code == 404

    # u2 tries to start u1's session
    with pytest.raises(HTTPException) as exc_info:
        activity_service.start_study_session(db_session, s1["id"], u2.id)
    assert exc_info.value.status_code == 404

    # u2 tries to complete u1's session
    with pytest.raises(HTTPException) as exc_info:
        activity_service.complete_study_session(db_session, s1["id"], u2.id, actual_duration_minutes=30)
    assert exc_info.value.status_code == 404


def test_11_transaction_rollback_upon_failure(db_session, seeded_users_and_subjects):
    """11. State transitions are atomic and rollback cleanly on database error."""
    u1 = seeded_users_and_subjects["u1"]
    sub1 = seeded_users_and_subjects["sub1"]

    s1 = activity_service.create_study_session(
        db_session, u1.id, StudySessionCreate(subject_id=sub1.id, date="2026-11-26", duration_minutes=45)
    )

    # Simulate an error by attempting an invalid status transition
    with pytest.raises(HTTPException):
        activity_service.update_study_session(
            db_session, s1["id"], u1.id, StudySessionUpdate(status="invalid_status_xyz")
        )

    # Session status must remain pending
    refetched = activity_service.get_study_session_by_id(db_session, s1["id"], u1.id)
    assert refetched["status"] == "pending"


def test_12_existing_session_backward_compatibility(db_session, seeded_users_and_subjects):
    """12. Existing historical sessions with NULL started_at and actual_duration remain compatible."""
    u1 = seeded_users_and_subjects["u1"]
    sub1 = seeded_users_and_subjects["sub1"]

    # Directly insert legacy row resembling historical records
    legacy = StudySession(
        user_id=u1.id,
        subject_id=sub1.id,
        date="2026-11-10",
        duration_minutes=50,
        status="completed",
        started_at=None,
        completed_at=datetime(2026, 11, 10, 15, 0, 0, tzinfo=timezone.utc),
        actual_duration_minutes=None,
    )
    db_session.add(legacy)
    db_session.commit()

    fetched = activity_service.get_study_session_by_id(db_session, legacy.id, u1.id)
    assert fetched["status"] == "completed"
    assert fetched["duration_minutes"] == 50
    assert fetched["actual_duration_minutes"] is None
    assert fetched["started_at"] is None
    assert fetched["completed_at"] is not None


def test_fastapi_endpoints_study_session_lifecycle(db_session, seeded_users_and_subjects):
    """Verifies complete HTTP API flow via FastAPI test client."""
    u1 = seeded_users_and_subjects["u1"]
    sub1 = seeded_users_and_subjects["sub1"]

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: u1

    client = TestClient(app)

    try:
        # 1. Create pending session
        res = client.post(
            "/api/study-sessions",
            json={"subject_id": sub1.id, "date": "2026-11-26", "duration_minutes": 45},
        )
        assert res.status_code == 201
        session_id = res.json()["id"]
        assert res.json()["status"] == "pending"

        # 2. Start session
        res_start = client.post(f"/api/study-sessions/{session_id}/start")
        assert res_start.status_code == 200
        assert res_start.json()["status"] == "in_progress"
        assert res_start.json()["started_at"] is not None

        # 3. Complete session
        res_comp = client.post(
            f"/api/study-sessions/{session_id}/complete",
            json={"actual_duration_minutes": 50},
        )
        assert res_comp.status_code == 200
        assert res_comp.json()["status"] == "completed"
        assert res_comp.json()["duration_minutes"] == 45
        assert res_comp.json()["actual_duration_minutes"] == 50

        # 4. Attempt duplicate completion -> 400
        res_dup = client.post(
            f"/api/study-sessions/{session_id}/complete",
            json={"actual_duration_minutes": 55},
        )
        assert res_dup.status_code == 400

        # 5. Create another session and abandon it
        res2 = client.post(
            "/api/study-sessions",
            json={"subject_id": sub1.id, "date": "2026-11-26", "duration_minutes": 60},
        )
        s2_id = res2.json()["id"]
        client.post(f"/api/study-sessions/{s2_id}/start")
        res_aband = client.post(
            f"/api/study-sessions/{s2_id}/abandon",
            json={"actual_duration_minutes": 15, "reason": "Tired"},
        )
        assert res_aband.status_code == 200
        assert res_aband.json()["status"] == "abandoned"
        assert res_aband.json()["actual_duration_minutes"] == 15
        assert res_aband.json()["duration_minutes"] == 60
    finally:
        app.dependency_overrides.clear()
