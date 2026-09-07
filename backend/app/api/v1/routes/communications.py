from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.db.models import CommunicationLog, NotificationPreference, User
from app.services.communication_providers import DevelopmentEmailProvider, DevelopmentVoiceProvider

router = APIRouter()


class EmailTestRequest(BaseModel):
    subject: str = Field(..., min_length=3)
    message: str = Field(..., min_length=3)


class CallTestRequest(BaseModel):
    message: str = Field(..., min_length=3)


@router.post("/email/test")
def test_email(payload: EmailTestRequest, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    result = DevelopmentEmailProvider().send(user.email, payload.subject, payload.message)
    log = CommunicationLog(user_id=user_id, communication_type="email", provider=result.provider, status=result.status, consent_state="not_required")
    db.add(log)
    db.commit()
    return {"status": result.status, "provider": result.provider, "detail": result.detail}


@router.post("/call/test")
def test_call(payload: CallTestRequest, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    preferences = db.query(NotificationPreference).filter(NotificationPreference.user_id == user_id).first()
    if not user or not preferences or not preferences.voice_enabled or not preferences.phone_consent or not user.phone_number:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Voice calls require a phone number, enabled voice notifications, and explicit consent")
    result = DevelopmentVoiceProvider().send(user.phone_number, payload.message)
    db.add(CommunicationLog(user_id=user_id, communication_type="voice", provider=result.provider, status=result.status, consent_state="consented"))
    db.commit()
    return {"status": result.status, "provider": result.provider, "detail": result.detail}


@router.get("/history")
def communication_history(db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    logs = db.query(CommunicationLog).filter(CommunicationLog.user_id == user_id).order_by(CommunicationLog.created_at.desc(), CommunicationLog.id.desc()).all()
    return [{"id": log.id, "type": log.communication_type, "provider": log.provider, "status": log.status, "failure_reason": log.failure_reason, "consent_state": log.consent_state, "created_at": log.created_at} for log in logs]
