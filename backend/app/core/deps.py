from collections.abc import Generator

from fastapi import Depends
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import User
from app.core.security import get_current_user


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# LEGACY — do not use.
# These stubs return a hardcoded "demo-user" and bypass real authentication.
# No active route imports them (all protected endpoints use get_current_user /
# require_supervisor).  Kept only so old code that may still reference them
# does not crash; remove once all references are confirmed gone.
# ---------------------------------------------------------------------------

async def get_current_user_id() -> str:
    return "demo-user"


async def require_auth() -> str:
    return "demo-user"


def require_supervisor(user_id: int = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if user.role != "supervisor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Supervisor access required")
    return user
