import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db

test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session() -> Session:
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> TestClient:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def user_a_auth(client: TestClient) -> dict:
    client.post(
        "/api/auth/register",
        json={"email": "planner_a@neurolearn.edu", "password": "Password123", "full_name": "Planner A"},
    )
    login_res = client.post(
        "/api/auth/login",
        json={"email": "planner_a@neurolearn.edu", "password": "Password123"},
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def user_b_auth(client: TestClient) -> dict:
    client.post(
        "/api/auth/register",
        json={"email": "planner_b@neurolearn.edu", "password": "Password123", "full_name": "Planner B"},
    )
    login_res = client.post(
        "/api/auth/login",
        json={"email": "planner_b@neurolearn.edu", "password": "Password123"},
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def setup_curriculum(client: TestClient, user_a_auth: dict) -> dict:
    sub_res = client.post(
        "/api/subjects",
        headers=user_a_auth,
        json={"name": "Machine Learning", "code": "CS601"},
    )
    subject_id = sub_res.json()["id"]

    top_res = client.post(
        f"/api/subjects/{subject_id}/topics",
        headers=user_a_auth,
        json={"name": "Convolutional Neural Networks", "difficulty": "Medium"},
    )
    topic_id = top_res.json()["id"]

    return {"subject_id": subject_id, "topic_id": topic_id}


# ==============================================================================
# STUDY PLANNER TESTS
# ==============================================================================

def test_daily_and_week_study_plan(client: TestClient, user_a_auth: dict, setup_curriculum: dict):
    subject_id = setup_curriculum["subject_id"]
    topic_id = setup_curriculum["topic_id"]

    # Seed 2 tasks on 2026-11-26
    client.post(
        "/api/study-sessions",
        headers=user_a_auth,
        json={
            "subject_id": subject_id,
            "topic_id": topic_id,
            "session_date": "2026-11-26",
            "duration_minutes": 60,
            "status": "completed",
        },
    )
    client.post(
        "/api/study-sessions",
        headers=user_a_auth,
        json={
            "subject_id": subject_id,
            "topic_id": topic_id,
            "session_date": "2026-11-26",
            "duration_minutes": 45,
            "status": "pending",
        },
    )

    # 1. Fetch Daily Plan
    res = client.get("/api/study-plan?date=2026-11-26", headers=user_a_auth)
    assert res.status_code == 200
    plan = res.json()
    assert plan["date"] == "2026-11-26"
    assert plan["totalSessions"] == 2
    assert plan["completedSessions"] == 1
    assert plan["totalMinutes"] == 105
    assert len(plan["sessions"]) == 2

    # 2. Fetch Week Plan
    week_res = client.get("/api/study-plan/week", headers=user_a_auth)
    assert week_res.status_code == 200
    assert len(week_res.json()) >= 2


def test_task_status_toggle_and_reschedule(client: TestClient, user_a_auth: dict, setup_curriculum: dict):
    subject_id = setup_curriculum["subject_id"]
    topic_id = setup_curriculum["topic_id"]

    # Create session
    sess_res = client.post(
        "/api/study-sessions",
        headers=user_a_auth,
        json={"subject_id": subject_id, "topic_id": topic_id, "session_date": "2026-11-26"},
    )
    task_id = sess_res.json()["id"]

    # Complete task
    toggle_res = client.post(
        "/api/study-plan/complete",
        headers=user_a_auth,
        json={"taskId": task_id, "status": "completed"},
    )
    assert toggle_res.status_code == 200
    assert toggle_res.json()["newStatus"] == "completed"

    # Reschedule task
    resched_res = client.post(
        "/api/study-plan/reschedule",
        headers=user_a_auth,
        json={
            "taskId": task_id,
            "newDate": "2026-11-28",
            "newSlot": "02:00 PM - 03:30 PM",
            "reason": "Doctor appointment",
        },
    )
    assert resched_res.status_code == 200
    assert resched_res.json()["success"] is True
    assert resched_res.json()["task"]["date"] == "2026-11-28"
    assert resched_res.json()["task"]["time_slot"] == "02:00 PM - 03:30 PM"


# ==============================================================================
# RECOMMENDATIONS TESTS
# ==============================================================================

def test_recommendations_workflow_and_feedback(
    client: TestClient, user_a_auth: dict, user_b_auth: dict, setup_curriculum: dict
):
    subject_id = setup_curriculum["subject_id"]
    topic_id = setup_curriculum["topic_id"]

    # Manually seed a recommendation in DB for User A
    from app.models.entities import Recommendation
    with TestingSessionLocal() as session:
        rec = Recommendation(
            user_id="user_a_temp",  # Will be resolved
            subject_id=subject_id,
            topic_id=topic_id,
            agent_element="Performance Element",
            type="retention_decay",
            priority="high",
            title="Revise CNN Filters",
            reason_type="Forgetting Curve",
            reason_detail="Retention estimated at 55% after 5 days of decay.",
            suggested_slot="Evening",
            estimated_duration_minutes=45,
            status="pending",
        )

    # Let's use the DB session directly through client
    from app.core.security import decode_access_token
    token_str = user_a_auth["Authorization"].split(" ")[1]
    user_a_id = decode_access_token(token_str)

    with TestingSessionLocal() as session:
        rec.user_id = user_a_id
        session.add(rec)
        session.commit()
        session.refresh(rec)
        rec_id = rec.id

    # 1. Fetch recommendations list
    list_res = client.get("/api/recommendations", headers=user_a_auth)
    assert list_res.status_code == 200
    recs = list_res.json()
    assert len(recs) == 1
    assert recs[0]["id"] == rec_id

    # 2. Fetch recommendations hub
    hub_res = client.get("/api/recommendations/hub", headers=user_a_auth)
    assert hub_res.status_code == 200
    hub_data = hub_res.json()
    assert hub_data["totalPending"] == 1
    assert len(hub_data["activeRecommendations"]) == 1
    assert hub_data["countsByElement"]["Performance Element"] == 1

    # 3. Record student feedback (helpful: True)
    fb_res = client.post(
        f"/api/recommendations/{rec_id}/feedback",
        headers=user_a_auth,
        json={"helpful": True, "note": "Great recommendation"},
    )
    assert fb_res.status_code == 200
    assert fb_res.json()["feedback_helpful"] is True
    assert fb_res.json()["feedback_note"] == "Great recommendation"

    # 4. Accept recommendation (automatically schedules study session)
    accept_res = client.post(f"/api/recommendations/{rec_id}/accept", headers=user_a_auth)
    assert accept_res.status_code == 200
    assert accept_res.json()["status"] == "accepted"

    # Verify that a study session was automatically added to schedule
    sessions_res = client.get("/api/study-sessions", headers=user_a_auth)
    assert sessions_res.status_code == 200
    assert any("Revise CNN Filters" in s["title"] for s in sessions_res.json())

    # 5. Cross-student data isolation: User B cannot access User A's recommendation
    assert client.get(f"/api/recommendations/{rec_id}", headers=user_b_auth).status_code == 404
    assert client.post(f"/api/recommendations/{rec_id}/dismiss", headers=user_b_auth).status_code == 404
    assert client.post(f"/api/recommendations/{rec_id}/feedback", headers=user_b_auth, json={"helpful": False}).status_code == 404
