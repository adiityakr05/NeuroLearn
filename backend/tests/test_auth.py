from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from app.models.entities import User


# ==============================================================================
# 1. SECURITY & PASSWORD TESTS
# ==============================================================================

def test_password_hashing_and_verification():
    raw_password = "SuperSecretPassword123!"
    hashed = hash_password(raw_password)

    # Argon2 hash format check
    assert hashed.startswith("$argon2id$")
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_token_generation_and_validation():
    user_id = "test-user-uuid-1234"
    token = create_access_token(subject=user_id)
    assert isinstance(token, str)

    decoded_id = decode_access_token(token)
    assert decoded_id == user_id


def test_invalid_and_expired_jwt_token():
    # Invalid token string
    assert decode_access_token("not.a.valid.jwt.token") is None

    # Token signed with another secret (at least 32 bytes to avoid InsecureKeyLengthWarning)
    import jwt
    foreign_token = jwt.encode(
        {"sub": "123"},
        "wrong-secret-key-that-is-at-least-32-bytes-long",
        algorithm="HS256",
    )
    assert decode_access_token(foreign_token) is None


# ==============================================================================
# 2. REGISTRATION ENDPOINT TESTS
# ==============================================================================

def test_successful_registration(client: TestClient):
    payload = {
        "email": "student@college.edu",
        "password": "Password123!",
        "full_name": "Aditya Kumar",
        "program": "B.Tech Computer Science & AI",
        "semester": "Semester 6",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["email"] == "student@college.edu"
    assert data["full_name"] == "Aditya Kumar"
    assert "id" in data
    assert "hashed_password" not in data  # Verifies password hash is never exposed


def test_duplicate_email_registration_fails(client: TestClient):
    payload = {
        "email": "duplicate@college.edu",
        "password": "Password123!",
        "full_name": "Original Student",
    }
    res1 = client.post("/api/auth/register", json=payload)
    assert res1.status_code == 201

    # Attempting duplicate registration
    res2 = client.post("/api/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]


# ==============================================================================
# 3. LOGIN & TOKEN TESTS
# ==============================================================================

def test_successful_login(client: TestClient):
    # Register first
    client.post(
        "/api/auth/register",
        json={"email": "login_test@college.edu", "password": "ValidPassword123", "full_name": "Login User"},
    )

    # Login
    login_res = client.post(
        "/api/auth/login",
        json={"email": "login_test@college.edu", "password": "ValidPassword123"},
    )
    assert login_res.status_code == 200
    data = login_res.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "login_test@college.edu"
    assert "hashed_password" not in data["user"]


def test_login_incorrect_password(client: TestClient):
    client.post(
        "/api/auth/register",
        json={"email": "wrong_pw@college.edu", "password": "CorrectPassword", "full_name": "User"},
    )

    login_res = client.post(
        "/api/auth/login",
        json={"email": "wrong_pw@college.edu", "password": "IncorrectPassword"},
    )
    assert login_res.status_code == 401
    assert "Incorrect email or password" in login_res.json()["detail"]


def test_login_nonexistent_email(client: TestClient):
    login_res = client.post(
        "/api/auth/login",
        json={"email": "does_not_exist@college.edu", "password": "Password123"},
    )
    assert login_res.status_code == 401


# ==============================================================================
# 4. PROTECTED ENDPOINTS & USER PROFILE TESTS
# ==============================================================================

def test_protected_endpoints_without_token(client: TestClient):
    res_auth_me = client.get("/api/auth/me")
    assert res_auth_me.status_code == 401

    res_users_me = client.get("/api/users/me")
    assert res_users_me.status_code == 401


def test_protected_endpoints_with_valid_token(client: TestClient):
    # Register and login
    client.post(
        "/api/auth/register",
        json={"email": "token_user@college.edu", "password": "Password123", "full_name": "Token User"},
    )
    login_res = client.post(
        "/api/auth/login",
        json={"email": "token_user@college.edu", "password": "Password123"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Access /api/auth/me
    res_me = client.get("/api/auth/me", headers=headers)
    assert res_me.status_code == 200
    assert res_me.json()["email"] == "token_user@college.edu"

    # Access /api/users/me
    res_users = client.get("/api/users/me", headers=headers)
    assert res_users.status_code == 200
    assert res_users.json()["full_name"] == "Token User"


def test_user_profile_update(client: TestClient):
    client.post(
        "/api/auth/register",
        json={"email": "update_me@college.edu", "password": "Password123", "full_name": "Old Name"},
    )
    login_res = client.post(
        "/api/auth/login",
        json={"email": "update_me@college.edu", "password": "Password123"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Update profile fields
    patch_res = client.patch(
        "/api/users/me",
        headers=headers,
        json={
            "full_name": "New Full Name",
            "semester": "Semester 7",
            "avatar_url": "https://example.com/avatar.png",
        },
    )
    assert patch_res.status_code == 200
    updated_data = patch_res.json()
    assert updated_data["full_name"] == "New Full Name"
    assert updated_data["semester"] == "Semester 7"
    assert updated_data["avatar_url"] == "https://example.com/avatar.png"
    assert updated_data["email"] == "update_me@college.edu"  # Unchanged


def test_oauth2_form_token_endpoint(client: TestClient):
    # Register test user
    client.post(
        "/api/auth/register",
        json={"email": "swagger_user@college.edu", "password": "SwaggerPassword123", "full_name": "Swagger User"},
    )

    # Test OAuth2 form login via POST /api/auth/token
    form_res = client.post(
        "/api/auth/token",
        data={"username": "swagger_user@college.edu", "password": "SwaggerPassword123"},
    )
    assert form_res.status_code == 200
    form_data = form_res.json()
    assert "access_token" in form_data
    assert form_data["token_type"] == "bearer"
    assert form_data["user"]["email"] == "swagger_user@college.edu"

    # Verify that the generated token authenticates on protected endpoints
    token = form_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "swagger_user@college.edu"

    # Test failed login with invalid credentials via /api/auth/token
    bad_res = client.post(
        "/api/auth/token",
        data={"username": "swagger_user@college.edu", "password": "WrongPassword"},
    )
    assert bad_res.status_code == 401
