"""CLI seed script for the ResearchOS demo account."""

import sys
from pathlib import Path

_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from app.db.session import SessionLocal
from app.services.demo_service import ensure_demo_account, DEMO_EMAIL, DEMO_PASSWORD


def main() -> None:
    print(f"Seeding demo account ({DEMO_EMAIL})...")
    with SessionLocal() as db:
        user = ensure_demo_account(db)
        print(f"Demo account ready: ID={user.id}, Email={user.email}, Verified={user.email_verified}")
        print(f"Password: {DEMO_PASSWORD}")


if __name__ == "__main__":
    main()
