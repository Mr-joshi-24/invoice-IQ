import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from backend.app.models.user import UserRole

client = TestClient(app)


def test_password_hashing_and_verification():
    raw_pass = "SecurePass123!"
    hashed = hash_password(raw_pass)
    assert hashed != raw_pass
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_creation_and_decoding():
    token = create_access_token(subject="user_12345", role=UserRole.ADMIN, extra_claims={"email": "test@example.com"})
    assert isinstance(token, str)
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "user_12345"
    assert payload["role"] == UserRole.ADMIN
    assert payload["email"] == "test@example.com"
    assert "exp" in payload


def test_user_registration_flow():
    email = "new_auditor@invoiceiq.com"
    payload = {
        "email": email,
        "password": "Password123!",
        "full_name": "Test Auditor",
        "role": UserRole.REVIEWER
    }
    # 1. Register new user
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code in [201, 400]  # 400 if already seeded
    if res.status_code == 201:
        data = res.json()
        assert data["email"] == email
        assert data["role"] == UserRole.REVIEWER
        assert "hashed_password" not in data
        assert "id" in data

    # 2. Duplicate registration rejected
    res_dup = client.post("/api/v1/auth/register", json=payload)
    assert res_dup.status_code == 400
    assert "already exists" in res_dup.json()["detail"]


def test_user_login_success_and_failure():
    # 1. Successful Login with seeded Admin
    login_success = client.post("/api/v1/auth/login", json={
        "email": "admin@invoiceiq.com",
        "password": "Admin@123"
    })
    assert login_success.status_code == 200
    data = login_success.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["role"] == UserRole.ADMIN

    # 2. Failed Login with invalid password
    login_fail = client.post("/api/v1/auth/login", json={
        "email": "admin@invoiceiq.com",
        "password": "IncorrectPassword"
    })
    assert login_fail.status_code == 401
    assert "Incorrect email or password" in login_fail.json()["detail"]

    # 3. Failed Login with non-existent email
    login_nonexistent = client.post("/api/v1/auth/login", json={
        "email": "nobody@nowhere.com",
        "password": "Password123"
    })
    assert login_nonexistent.status_code == 401


def test_protected_me_endpoint():
    # 1. Unauthenticated request rejected
    res_unauth = client.get("/api/v1/auth/me")
    assert res_unauth.status_code == 401

    # 2. Authenticated request with valid token
    login_res = client.post("/api/v1/auth/login", json={
        "email": "auditor@invoiceiq.com",
        "password": "Auditor@123"
    })
    token = login_res.json()["access_token"]

    res_auth = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_auth.status_code == 200
    profile = res_auth.json()
    assert profile["email"] == "auditor@invoiceiq.com"
    assert profile["role"] == UserRole.REVIEWER


def test_rbac_admin_vs_reviewer_permissions():
    # 1. Login as Admin
    admin_login = client.post("/api/v1/auth/login", json={
        "email": "admin@invoiceiq.com",
        "password": "Admin@123"
    })
    admin_token = admin_login.json()["access_token"]

    # Admin CAN access /auth/users
    res_admin = client.get("/api/v1/auth/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin.status_code == 200
    users_list = res_admin.json()
    assert len(users_list) >= 2

    # 2. Login as Reviewer
    reviewer_login = client.post("/api/v1/auth/login", json={
        "email": "auditor@invoiceiq.com",
        "password": "Auditor@123"
    })
    reviewer_token = reviewer_login.json()["access_token"]

    # Reviewer CANNOT access /auth/users (HTTP 403 Forbidden)
    res_forbidden = client.get("/api/v1/auth/users", headers={"Authorization": f"Bearer {reviewer_token}"})
    assert res_forbidden.status_code == 403
    assert "Access denied" in res_forbidden.json()["detail"]

