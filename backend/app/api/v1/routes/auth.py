"""Standard Authentication Routes for ResearchOS.

Features clean registration, direct login, and secure token validation.
Email verification, OTP, and password reset workflows have been removed.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_db
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.db.models import User
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    RegistrationResponse,
    TokenResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_optional_auth = HTTPBearer(auto_error=False)


def _extract_user_id_from_token(credentials: HTTPAuthorizationCredentials | None) -> int | None:
    """Safely extract user_id from a bearer token. Returns None on failure."""
    if credentials is None:
        return None
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        sub = payload.get("sub")
        if sub is not None:
            return int(sub)
    except (JWTError, TypeError, ValueError):
        pass
    return None


# ---------------------------------------------------------
# REGISTER USER — Direct Account Creation (No OTP / Verification)
# ---------------------------------------------------------

@router.post(
    "/register",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> RegistrationResponse:
    email = str(payload.email).strip().lower()
    name = payload.name.strip()

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required.",
        )

    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name is required.",
        )

    if payload.confirm_password is not None and payload.password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match.",
        )

    # Check duplicate email addresses
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists. Please sign in.",
        )

    # Create user directly with email_verified=True
    user = User(
        email=email,
        name=name,
        password_hash=hash_password(payload.password),
        email_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("[Auth] New user registered directly: %s (id: %d)", email, user.id)

    token = create_access_token(subject=str(user.id))

    return RegistrationResponse(
        message="Account created successfully.",
        email=email,
        access_token=token,
        token_type="bearer",
        user_id=user.id,
    )


# ---------------------------------------------------------
# LOGIN USER — Direct Authentication
# ---------------------------------------------------------

@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    email = str(payload.email).strip().lower()

    users = db.query(User).filter(User.email == email).all()

    if not users:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    matched_user = None
    for user in users:
        if verify_password(payload.password, user.password_hash):
            matched_user = user
            break

    if not matched_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # Allow direct login without email_verified gating
    token = create_access_token(subject=str(matched_user.id))

    logger.info("[Auth] User logged in: %s (id: %d)", email, matched_user.id)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=matched_user.id,
        email=matched_user.email,
        name=matched_user.name,
        message="Login successful.",
    )


# ---------------------------------------------------------
# CURRENT USER PROFILE
# ---------------------------------------------------------

@router.get("/me")
def me(
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == current_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "email_verified": True,
        "phone_number": getattr(user, "phone_number", None),
        "created_at": user.created_at,
    }
