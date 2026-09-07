from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.db.repositories.notification_repository import NotificationRepository
from app.schemas.reviews import NotificationResponse

router = APIRouter()


@router.get("/", response_model=list[NotificationResponse])
def list_notifications(db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    return NotificationRepository(db).list_for_user(user_id)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(notification_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    notification = NotificationRepository(db).get_for_user(notification_id, user_id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return NotificationRepository(db).mark_read(notification)
