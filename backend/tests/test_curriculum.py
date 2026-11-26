import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.base import Base
from app.db.session import get_db


@pytest.fixture(scope="function")
def user_a_auth(client: TestClient) -> dict:
    # Register and login User A
    client.post(
        "/api/auth/register",
        json={"email": "student_a@neurolearn.edu", "password": "Password123", "full_name": "Student A"},
    )
    login_res = client.post(
        "/api/auth/login",
        json={"email": "student_a@neurolearn.edu", "password": "Password123"},
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def user_b_auth(client: TestClient) -> dict:
    # Register and login User B
    client.post(
        "/api/auth/register",
        json={"email": "student_b@neurolearn.edu", "password": "Password123", "full_name": "Student B"},
    )
    login_res = client.post(
        "/api/auth/login",
        json={"email": "student_b@neurolearn.edu", "password": "Password123"},
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# SUBJECT TESTS
# ==============================================================================

def test_subject_unauthenticated_access_rejected(client: TestClient):
    res = client.get("/api/subjects")
    assert res.status_code == 401

    res = client.post("/api/subjects", json={"name": "Math", "code": "MATH101"})
    assert res.status_code == 401


def test_subject_creation_and_retrieval(client: TestClient, user_a_auth: dict):
    # Create Subject
    payload = {
        "name": "Machine Learning",
        "code": "CS601",
        "color": "#6366F1",
        "description": "Foundations of Supervised and Unsupervised Learning",
        "target_mastery": 85.0,
    }
    create_res = client.post("/api/subjects", headers=user_a_auth, json=payload)
    assert create_res.status_code == 201
    subject_data = create_res.json()
    assert subject_data["name"] == "Machine Learning"
    assert subject_data["code"] == "CS601"
    assert "id" in subject_data
    subject_id = subject_data["id"]

    # Retrieve Individual Subject
    get_res = client.get(f"/api/subjects/{subject_id}", headers=user_a_auth)
    assert get_res.status_code == 200
    retrieved = get_res.json()
    assert retrieved["id"] == subject_id
    assert retrieved["code"] == "CS601"
    assert "topics" in retrieved
    assert isinstance(retrieved["topics"], list)


def test_subject_duplicate_code_rejected_for_same_user(client: TestClient, user_a_auth: dict):
    payload = {"name": "Algorithms 1", "code": "CS604"}
    res1 = client.post("/api/subjects", headers=user_a_auth, json=payload)
    assert res1.status_code == 201

    payload_dup = {"name": "Algorithms 2", "code": "CS604"}
    res2 = client.post("/api/subjects", headers=user_a_auth, json=payload_dup)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]


def test_subject_listing_pagination_and_search(client: TestClient, user_a_auth: dict):
    # Seed 3 subjects
    for i in range(1, 4):
        client.post(
            "/api/subjects",
            headers=user_a_auth,
            json={"name": f"Course {i}", "code": f"CSE{100 + i}"},
        )

    # List all
    list_res = client.get("/api/subjects", headers=user_a_auth)
    assert list_res.status_code == 200
    subjects = list_res.json()
    assert len(subjects) == 3

    # Pagination: limit=1, skip=1
    page_res = client.get("/api/subjects?skip=1&limit=1", headers=user_a_auth)
    assert page_res.status_code == 200
    paged_subjects = page_res.json()
    assert len(paged_subjects) == 1

    # Search by code
    search_res = client.get("/api/subjects?search=CSE102", headers=user_a_auth)
    assert search_res.status_code == 200
    assert len(search_res.json()) == 1
    assert search_res.json()[0]["code"] == "CSE102"


def test_subject_update(client: TestClient, user_a_auth: dict):
    create_res = client.post(
        "/api/subjects",
        headers=user_a_auth,
        json={"name": "Old Subject Name", "code": "OLD101", "color": "#000000"},
    )
    subject_id = create_res.json()["id"]

    # Patch update
    update_res = client.patch(
        f"/api/subjects/{subject_id}",
        headers=user_a_auth,
        json={"name": "New Subject Name", "color": "#10B981"},
    )
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["name"] == "New Subject Name"
    assert updated["color"] == "#10B981"
    assert updated["code"] == "OLD101"

    # PUT alias update
    put_res = client.put(
        f"/api/subjects/{subject_id}",
        headers=user_a_auth,
        json={"name": "PUT Subject Name"},
    )
    assert put_res.status_code == 200
    assert put_res.json()["name"] == "PUT Subject Name"


def test_subject_deletion_cascades(client: TestClient, user_a_auth: dict):
    # Create subject
    subj_res = client.post(
        "/api/subjects",
        headers=user_a_auth,
        json={"name": "Temporary Subject", "code": "TEMP999"},
    )
    subject_id = subj_res.json()["id"]

    # Create topic under subject
    topic_res = client.post(
        f"/api/subjects/{subject_id}/topics",
        headers=user_a_auth,
        json={"name": "Topic to Cascade Delete"},
    )
    assert topic_res.status_code == 201
    topic_id = topic_res.json()["id"]

    # Delete subject
    del_res = client.delete(f"/api/subjects/{subject_id}", headers=user_a_auth)
    assert del_res.status_code == 204

    # Verify subject is gone
    get_subj = client.get(f"/api/subjects/{subject_id}", headers=user_a_auth)
    assert get_subj.status_code == 404

    # Verify topic is cascade deleted
    get_topic = client.get(f"/api/topics/{topic_id}", headers=user_a_auth)
    assert get_topic.status_code == 404


# ==============================================================================
# TOPIC TESTS
# ==============================================================================

def test_topic_creation_and_retrieval(client: TestClient, user_a_auth: dict):
    # Create subject first
    subj_res = client.post(
        "/api/subjects",
        headers=user_a_auth,
        json={"name": "Database Systems", "code": "CS602"},
    )
    subject_id = subj_res.json()["id"]

    # Create Topic
    topic_payload = {
        "name": "B+ Trees Insertion & Balancing",
        "difficulty": "Hard",
        "mastery_score": 75.0,
        "retention_score": 80.0,
        "completed": False,
    }
    create_topic_res = client.post(
        f"/api/subjects/{subject_id}/topics",
        headers=user_a_auth,
        json=topic_payload,
    )
    assert create_topic_res.status_code == 201
    topic_data = create_topic_res.json()
    assert topic_data["name"] == "B+ Trees Insertion & Balancing"
    assert topic_data["difficulty"] == "Hard"
    assert topic_data["mastery_score"] == 75.0
    topic_id = topic_data["id"]

    # Retrieve Individual Topic
    get_topic_res = client.get(f"/api/topics/{topic_id}", headers=user_a_auth)
    assert get_topic_res.status_code == 200
    assert get_topic_res.json()["id"] == topic_id


def test_topic_duplicate_name_rejected_within_subject(client: TestClient, user_a_auth: dict):
    subj_res = client.post(
        "/api/subjects",
        headers=user_a_auth,
        json={"name": "Operating Systems", "code": "CS603"},
    )
    subject_id = subj_res.json()["id"]

    # Add topic 1
    res1 = client.post(
        f"/api/subjects/{subject_id}/topics",
        headers=user_a_auth,
        json={"name": "Virtual Memory"},
    )
    assert res1.status_code == 201

    # Duplicate topic name in same subject
    res2 = client.post(
        f"/api/subjects/{subject_id}/topics",
        headers=user_a_auth,
        json={"name": "Virtual Memory"},
    )
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]


def test_topic_listing_and_search(client: TestClient, user_a_auth: dict):
    subj_res = client.post(
        "/api/subjects",
        headers=user_a_auth,
        json={"name": "Network Protocols", "code": "CS605"},
    )
    subject_id = subj_res.json()["id"]

    # Add topics
    client.post(f"/api/subjects/{subject_id}/topics", headers=user_a_auth, json={"name": "TCP Handshake"})
    client.post(f"/api/subjects/{subject_id}/topics", headers=user_a_auth, json={"name": "UDP Streaming"})

    # List
    list_res = client.get(f"/api/subjects/{subject_id}/topics", headers=user_a_auth)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 2

    # Search
    search_res = client.get(f"/api/subjects/{subject_id}/topics?search=TCP", headers=user_a_auth)
    assert search_res.status_code == 200
    assert len(search_res.json()) == 1
    assert search_res.json()[0]["name"] == "TCP Handshake"


def test_topic_update_and_delete(client: TestClient, user_a_auth: dict):
    subj_res = client.post(
        "/api/subjects",
        headers=user_a_auth,
        json={"name": "Discrete Math", "code": "DM101"},
    )
    subject_id = subj_res.json()["id"]

    topic_res = client.post(
        f"/api/subjects/{subject_id}/topics",
        headers=user_a_auth,
        json={"name": "Graph Theory", "mastery_score": 40.0, "completed": False},
    )
    topic_id = topic_res.json()["id"]

    # PATCH /api/topics/{topic_id}
    patch_res = client.patch(
        f"/api/topics/{topic_id}",
        headers=user_a_auth,
        json={"mastery_score": 90.0, "completed": True},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["mastery_score"] == 90.0
    assert patch_res.json()["completed"] is True

    # PUT nested alias
    put_res = client.put(
        f"/api/subjects/{subject_id}/topics/{topic_id}",
        headers=user_a_auth,
        json={"difficulty": "Hard"},
    )
    assert put_res.status_code == 200
    assert put_res.json()["difficulty"] == "Hard"

    # DELETE /api/topics/{topic_id}
    del_res = client.delete(f"/api/topics/{topic_id}", headers=user_a_auth)
    assert del_res.status_code == 204

    # Verify 404
    assert client.get(f"/api/topics/{topic_id}", headers=user_a_auth).status_code == 404


def test_invalid_subject_id_handling(client: TestClient, user_a_auth: dict):
    res = client.post(
        "/api/subjects/non-existent-subject-id/topics",
        headers=user_a_auth,
        json={"name": "Invalid Topic"},
    )
    assert res.status_code == 404


# ==============================================================================
# MULTI-TENANT ISOLATION & SECURITY TESTS
# ==============================================================================

def test_student_isolation_subjects(client: TestClient, user_a_auth: dict, user_b_auth: dict):
    # Student A creates a subject
    res_a = client.post(
        "/api/subjects",
        headers=user_a_auth,
        json={"name": "Student A Secret Subject", "code": "SEC101"},
    )
    subject_id_a = res_a.json()["id"]

    # Student B cannot list Student A's subject
    list_b = client.get("/api/subjects", headers=user_b_auth)
    assert list_b.status_code == 200
    assert len(list_b.json()) == 0

    # Student B cannot retrieve Student A's subject
    get_b = client.get(f"/api/subjects/{subject_id_a}", headers=user_b_auth)
    assert get_b.status_code == 404

    # Student B cannot update Student A's subject
    patch_b = client.patch(
        f"/api/subjects/{subject_id_a}",
        headers=user_b_auth,
        json={"name": "Hacked Name"},
    )
    assert patch_b.status_code == 404

    # Student B cannot delete Student A's subject
    del_b = client.delete(f"/api/subjects/{subject_id_a}", headers=user_b_auth)
    assert del_b.status_code == 404

    # Subject still intact for Student A
    get_a = client.get(f"/api/subjects/{subject_id_a}", headers=user_a_auth)
    assert get_a.status_code == 200
    assert get_a.json()["name"] == "Student A Secret Subject"


def test_student_isolation_topics(client: TestClient, user_a_auth: dict, user_b_auth: dict):
    # Student A creates subject and topic
    res_subj_a = client.post(
        "/api/subjects",
        headers=user_a_auth,
        json={"name": "Subject A", "code": "SUBJA"},
    )
    subject_id_a = res_subj_a.json()["id"]

    res_topic_a = client.post(
        f"/api/subjects/{subject_id_a}/topics",
        headers=user_a_auth,
        json={"name": "Topic A"},
    )
    topic_id_a = res_topic_a.json()["id"]

    # Student B cannot create topic under Student A's subject
    res_b_create = client.post(
        f"/api/subjects/{subject_id_a}/topics",
        headers=user_b_auth,
        json={"name": "Injected Topic"},
    )
    assert res_b_create.status_code == 404

    # Student B cannot list topics under Student A's subject
    res_b_list = client.get(f"/api/subjects/{subject_id_a}/topics", headers=user_b_auth)
    assert res_b_list.status_code == 404

    # Student B cannot retrieve Student A's topic directly
    res_b_get = client.get(f"/api/topics/{topic_id_a}", headers=user_b_auth)
    assert res_b_get.status_code == 404

    # Student B cannot update Student A's topic
    res_b_patch = client.patch(
        f"/api/topics/{topic_id_a}",
        headers=user_b_auth,
        json={"name": "Tampered Topic Name"},
    )
    assert res_b_patch.status_code == 404

    # Student B cannot delete Student A's topic
    res_b_del = client.delete(f"/api/topics/{topic_id_a}", headers=user_b_auth)
    assert res_b_del.status_code == 404


def test_same_subject_code_allowed_for_different_students(client: TestClient, user_a_auth: dict, user_b_auth: dict):
    # Student A creates CS601
    res_a = client.post(
        "/api/subjects",
        headers=user_a_auth,
        json={"name": "Machine Learning", "code": "CS601"},
    )
    assert res_a.status_code == 201

    # Student B can also create CS601 independently
    res_b = client.post(
        "/api/subjects",
        headers=user_b_auth,
        json={"name": "Machine Learning", "code": "CS601"},
    )
    assert res_b.status_code == 201
