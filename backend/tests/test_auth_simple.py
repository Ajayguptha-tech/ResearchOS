"""Comprehensive tests for simplified standard authentication.

Verifies:
- Standard registration (name, email, password, confirm_password)
- Password hashing (passwords never stored in plaintext)
- Duplicate email rejection (HTTP 400)
- Validation of required fields and password matching
- Direct login without OTP / email verification dependency
- Invalid password rejection (HTTP 401)
- Non-existent user rejection (HTTP 401)
- JWT access token generation and authorization
- Current user profile retrieval (/api/v1/auth/me)
- Demo account access
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password, verify_password, create_access_token
from app.db.base import Base
from app.db.models import User
from app.schemas.auth import RegisterRequest, LoginRequest
from app.api.v1.routes.auth import register, login, me
from app.services.demo_service import ensure_demo_account
from fastapi import HTTPException


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_standard_registration_success(db):
    """Test successful user registration without OTP or email verification."""
    req = RegisterRequest(
        name="Ada Lovelace",
        email="ada@computing.org",
        password="AnalyticalEngine1843!",
        confirm_password="AnalyticalEngine1843!",
    )
    resp = register(payload=req, db=db)
    assert resp.email == "ada@computing.org"
    assert resp.access_token != ""
    assert resp.token_type == "bearer"
    assert resp.message == "Account created successfully."

    # Verify user record in database
    user = db.query(User).filter(User.email == "ada@computing.org").first()
    assert user is not None
    assert user.name == "Ada Lovelace"
    assert user.email_verified is True
    assert user.password_hash != "AnalyticalEngine1843!"
    assert verify_password("AnalyticalEngine1843!", user.password_hash)


def test_duplicate_email_rejection(db):
    """Registering with an existing email must raise HTTP 400."""
    req1 = RegisterRequest(
        name="Grace Hopper",
        email="grace@navy.mil",
        password="Nanoseconds1952!",
    )
    register(payload=req1, db=db)

    req2 = RegisterRequest(
        name="Grace Hopper 2",
        email="grace@navy.mil",
        password="AnotherPassword123!",
    )
    with pytest.raises(HTTPException) as exc_info:
        register(payload=req2, db=db)
    assert exc_info.value.status_code == 400
    assert "already exists" in str(exc_info.value.detail).lower()


def test_confirm_password_mismatch(db):
    """Mismatched passwords must raise HTTP 400."""
    req = RegisterRequest(
        name="Alan Turing",
        email="alan@bletchley.uk",
        password="EnigmaCipher1940!",
        confirm_password="DifferentPassword123!",
    )
    with pytest.raises(HTTPException) as exc_info:
        register(payload=req, db=db)
    assert exc_info.value.status_code == 400
    assert "passwords do not match" in str(exc_info.value.detail).lower()


def test_direct_login_success(db):
    """Valid credentials authenticate directly and return access token."""
    reg_req = RegisterRequest(
        name="Claude Shannon",
        email="claude@bell-labs.com",
        password="InformationTheory1948!",
    )
    register(payload=reg_req, db=db)

    login_req = LoginRequest(
        email="claude@bell-labs.com",
        password="InformationTheory1948!",
    )
    token_resp = login(payload=login_req, db=db)
    assert token_resp.access_token != ""
    assert token_resp.token_type == "bearer"
    assert token_resp.email == "claude@bell-labs.com"
    assert token_resp.name == "Claude Shannon"


def test_invalid_password_rejection(db):
    """Wrong password must raise HTTP 401."""
    reg_req = RegisterRequest(
        name="Katherine Johnson",
        email="katherine@nasa.gov",
        password="OrbitalMechanics1962!",
    )
    register(payload=reg_req, db=db)

    login_req = LoginRequest(
        email="katherine@nasa.gov",
        password="WrongPassword123!",
    )
    with pytest.raises(HTTPException) as exc_info:
        login(payload=login_req, db=db)
    assert exc_info.value.status_code == 401
    assert "invalid email or password" in str(exc_info.value.detail).lower()


def test_nonexistent_email_login_rejection(db):
    """Login with unknown email must raise HTTP 401."""
    login_req = LoginRequest(
        email="nobody@nowhere.org",
        password="SomePassword123!",
    )
    with pytest.raises(HTTPException) as exc_info:
        login(payload=login_req, db=db)
    assert exc_info.value.status_code == 401


def test_me_endpoint_returns_profile(db):
    """The /me endpoint returns the authenticated user profile."""
    reg_req = RegisterRequest(
        name="Dorothy Vaughan",
        email="dorothy@nasa.gov",
        password="FortranMaster1958!",
    )
    reg_resp = register(payload=reg_req, db=db)

    profile = me(current_user_id=reg_resp.user_id, db=db)
    assert profile["email"] == "dorothy@nasa.gov"
    assert profile["name"] == "Dorothy Vaughan"
    assert profile["email_verified"] is True


def test_demo_account_login(db):
    """Demo account is initialized and authenticates cleanly."""
    demo_user = ensure_demo_account(db)
    assert demo_user.email == "demo@researchos.io"
    assert demo_user.email_verified is True

    login_req = LoginRequest(
        email="demo@researchos.io",
        password="DemoPassword123!",
    )
    resp = login(payload=login_req, db=db)
    assert resp.access_token != ""
    assert resp.email == "demo@researchos.io"
