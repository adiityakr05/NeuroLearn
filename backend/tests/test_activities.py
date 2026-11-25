import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.base import Base
from app.db.session import get_db


@pytest.fixture(scope="function")
def user_a_auth(client: TestClient) -> dict:
    client.post(
        "/api/auth/register",
        json={"email": "student_alpha@neurolearn.edu", "password": "Password123", "full_name": "Student Alpha"},
    )
    login_res = client.post(
        "/api/auth/login",
        json={"email": "student_alpha@neurolearn.edu", "password": "Password123"},
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def user_b_auth(client: TestClient) -> dict:
    client.post(
        "/api/auth/register",
        json={"email": "student_beta@neurolearn.edu", "password": "Password123", "full_name": "Student Beta"},
    )
    login_res = client.post(
        "/api/auth/login",
        json={"email": "student_beta@neurolearn.edu", "password": "Password123"},
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def setup_curriculum(client: TestClient, user_a_auth: dict) -> dict:
    # Create Subject & Topic for User A
    sub_res = client.post(
        "/api/subjects",
        headers=user_a_auth,
        json={"name": "Machine Learning", "code": "CS601"},
    )
    subject_id = sub_res.json()["id"]

    top_res = client.post(
        f"/api/subjects/{subject_id}/topics",
        headers=user_a_auth,
        json={"name": "Backpropagation", "difficulty": "Hard"},
    )
    topic_id = top_res.json()["id"]

    return {"subject_id": subject_id, "topic_id": topic_id}


# ==============================================================================
# STUDY SESSIONS TESTS
# ==============================================================================

def test_study_session_crud(client: TestClient, user_a_auth: dict, setup_curriculum: dict):
    subject_id = setup_curriculum["subject_id"]
    topic_id = setup_curriculum["topic_id"]

    # 1. Create Session
    create_res = client.post(
        "/api/study-sessions",
        headers=user_a_auth,
        json={
            "subject_id": subject_id,
            "topic_id": topic_id,
            "title": "Backprop Derivations",
            "session_date": "2026-11-25",
            "time_slot": "09:00 AM - 10:30 AM",
            "duration_minutes": 90,
            "status": "pending",
            "priority": "high",
            "retention_score": 75.0,
        },
    )
    assert create_res.status_code == 201
    session_data = create_res.json()
    assert session_data["subject_id"] == subject_id
    assert session_data["topic_id"] == topic_id
    assert session_data["date"] == "2026-11-25"
    assert session_data["duration_minutes"] == 90
    session_id = session_data["id"]

    # 2. Get by ID
    get_res = client.get(f"/api/study-sessions/{session_id}", headers=user_a_auth)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == session_id

    # 3. List with Filters
    list_res = client.get(f"/api/study-sessions?subject_id={subject_id}&status=pending", headers=user_a_auth)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # 4. Update Session
    update_res = client.patch(
        f"/api/study-sessions/{session_id}",
        headers=user_a_auth,
        json={"status": "completed", "notes": "Completed backprop derivations cleanly"},
    )
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["status"] == "completed"
    assert updated["completed_at"] is not None

    # 5. Delete Session
    del_res = client.delete(f"/api/study-sessions/{session_id}", headers=user_a_auth)
    assert del_res.status_code == 204

    # Verify 404
    assert client.get(f"/api/study-sessions/{session_id}", headers=user_a_auth).status_code == 404


def test_study_session_validation_and_isolation(
    client: TestClient, user_a_auth: dict, user_b_auth: dict, setup_curriculum: dict
):
    subject_id = setup_curriculum["subject_id"]

    # Student B cannot create session referencing Student A's subject
    res_b = client.post(
        "/api/study-sessions",
        headers=user_b_auth,
        json={"subject_id": subject_id, "session_date": "2026-11-25"},
    )
    assert res_b.status_code == 404

    # Student A creates session
    res_a = client.post(
        "/api/study-sessions",
        headers=user_a_auth,
        json={"subject_id": subject_id, "session_date": "2026-11-25"},
    )
    sess_id = res_a.json()["id"]

    # Student B cannot access or modify Student A's session
    assert client.get(f"/api/study-sessions/{sess_id}", headers=user_b_auth).status_code == 404
    assert client.patch(f"/api/study-sessions/{sess_id}", headers=user_b_auth, json={"status": "completed"}).status_code == 404
    assert client.delete(f"/api/study-sessions/{sess_id}", headers=user_b_auth).status_code == 404


# ==============================================================================
# QUIZ ATTEMPTS TESTS
# ==============================================================================

def test_quiz_attempt_crud_and_validation(client: TestClient, user_a_auth: dict, setup_curriculum: dict):
    topic_id = setup_curriculum["topic_id"]

    # Invalid total_questions / correct_answers
    bad_res = client.post(
        "/api/quiz-attempts",
        headers=user_a_auth,
        json={"topic_id": topic_id, "total_questions": 5, "correct_answers": 8},
    )
    assert bad_res.status_code == 400

    # Valid Quiz Attempt
    quiz_res = client.post(
        "/api/quiz-attempts",
        headers=user_a_auth,
        json={
            "topic_id": topic_id,
            "title": "Calculus & Gradient Descent",
            "total_questions": 10,
            "correct_answers": 8,
            "time_taken_seconds": 320,
        },
    )
    assert quiz_res.status_code == 201
    quiz_data = quiz_res.json()
    assert quiz_data["accuracy"] == 80.0
    assert quiz_data["score_percentage"] == 80.0
    quiz_id = quiz_data["id"]

    # Retrieve Quiz Attempt
    get_res = client.get(f"/api/quiz-attempts/{quiz_id}", headers=user_a_auth)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == quiz_id

    # List Quiz Attempts
    list_res = client.get(f"/api/quiz-attempts?topic_id={topic_id}", headers=user_a_auth)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1


# ==============================================================================
# REVISION HISTORY TESTS
# ==============================================================================

def test_revision_history_crud_and_validation(client: TestClient, user_a_auth: dict, setup_curriculum: dict):
    topic_id = setup_curriculum["topic_id"]

    # Invalid score > 100
    bad_rev = client.post(
        "/api/revision-history",
        headers=user_a_auth,
        json={"topic_id": topic_id, "revision_date": "2026-11-25", "score": 120.0},
    )
    assert bad_rev.status_code == 422 or bad_rev.status_code == 400

    # Valid Revision Log
    rev_res = client.post(
        "/api/revision-history",
        headers=user_a_auth,
        json={
            "topic_id": topic_id,
            "revision_date": "2026-11-25",
            "score": 85.0,
            "mastery_score": 88.0,
            "retention_score": 90.0,
            "interval_days": 4,
            "repetition_number": 2,
            "notes": "Solved gradient backpropagation with momentum",
        },
    )
    assert rev_res.status_code == 201
    rev_data = rev_res.json()
    assert rev_data["score"] == 85.0
    rev_id = rev_data["id"]

    # Retrieve Revision
    get_res = client.get(f"/api/revision-history/{rev_id}", headers=user_a_auth)
    assert get_res.status_code == 200
    assert get_res.json()["notes"] == "Solved gradient backpropagation with momentum"

    # List Revisions
    list_res = client.get(f"/api/revision-history?topic_id={topic_id}", headers=user_a_auth)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1


# ==============================================================================
# PROGRESS TRACKING & AGGREGATE METRICS TESTS
# ==============================================================================

def test_progress_tracking_metrics(client: TestClient, user_a_auth: dict, setup_curriculum: dict):
    subject_id = setup_curriculum["subject_id"]
    topic_id = setup_curriculum["topic_id"]

    # Seed 1 completed session (60 mins)
    client.post(
        "/api/study-sessions",
        headers=user_a_auth,
        json={
            "subject_id": subject_id,
            "topic_id": topic_id,
            "session_date": "2026-11-20",
            "duration_minutes": 60,
            "status": "completed",
        },
    )

    # Seed 1 pending session (45 mins)
    client.post(
        "/api/study-sessions",
        headers=user_a_auth,
        json={
            "subject_id": subject_id,
            "topic_id": topic_id,
            "session_date": "2026-11-21",
            "duration_minutes": 45,
            "status": "pending",
        },
    )

    # Seed 1 Quiz attempt (80%)
    client.post(
        "/api/quiz-attempts",
        headers=user_a_auth,
        json={"topic_id": topic_id, "total_questions": 10, "correct_answers": 8},
    )

    # Seed 1 Revision
    client.post(
        "/api/revision-history",
        headers=user_a_auth,
        json={"topic_id": topic_id, "revision_date": "2026-11-21", "score": 85.0},
    )

    # Mark topic completed
    client.patch(f"/api/topics/{topic_id}", headers=user_a_auth, json={"completed": True})

    # Fetch Progress Overview
    prog_res = client.get("/api/analytics/progress", headers=user_a_auth)
    assert prog_res.status_code == 200
    data = prog_res.json()

    assert data["total_study_minutes"] == 60
    assert data["total_study_hours"] == 1.0
    assert data["total_sessions"] == 2
    assert data["completed_sessions"] == 1
    assert data["pending_sessions"] == 1
    assert data["total_subjects"] == 1
    assert data["total_topics"] == 1
    assert data["completed_topics"] == 1
    assert data["overall_progress_percentage"] == 100.0
    assert data["total_quiz_attempts"] == 1
    assert data["average_quiz_accuracy"] == 80.0
    assert data["total_revisions"] == 1

    # Validate subject-wise progress list
    assert len(data["subjects_progress"]) == 1
    subj_prog = data["subjects_progress"][0]
    assert subj_prog["subject_code"] == "CS601"
    assert subj_prog["total_topics"] == 1
    assert subj_prog["completed_topics"] == 1
    assert subj_prog["completed_sessions"] == 1
    assert subj_prog["total_study_minutes"] == 60

    # Validate topic-wise progress list
    assert len(data["topics_progress"]) == 1
    top_prog = data["topics_progress"][0]
    assert top_prog["topic_name"] == "Backpropagation"
    assert top_prog["completed"] is True
    assert top_prog["revision_count"] == 1
    assert top_prog["quiz_attempts_count"] == 1
