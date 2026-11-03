"""Cross-account security monitoring for approved administrators."""
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.api.routers.trust import require_remote
from app.db.models import AuthSession, SecurityAlertReview, SecurityEvent, User
from app.services.audit_service import record_security_event
from app.services.session_service import utc


router = APIRouter(prefix="/admin/monitoring", tags=["Administrator monitoring"])


class ReviewRequest(BaseModel):
    note: str = Field(min_length=8, max_length=500)


def require_monitoring_admin(
    request: Request, session: AuthSession = Depends(require_remote), db: Session = Depends(get_db),
) -> AuthSession:
    user = db.get(User, session.username)
    if request.headers.get("authorization") or session.client_type != "web" or not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Administrator monitoring access is required.")
    return session


def event_data(row: SecurityEvent) -> dict:
    return {
        "id": row.id, "event_type": row.event_type, "username": row.username,
        "ip_address": row.ip_address, "risk_level": row.risk_level,
        "details": row.details, "created_at": utc(row.created_at).isoformat(),
    }


@router.get("/summary")
def summary(_: AuthSession = Depends(require_monitoring_admin), db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    recent = db.query(SecurityEvent).filter(SecurityEvent.created_at >= since)
    open_high = db.query(func.count(SecurityEvent.id)).outerjoin(
        SecurityAlertReview, SecurityAlertReview.event_id == SecurityEvent.id,
    ).filter(SecurityEvent.risk_level == "HIGH", SecurityAlertReview.event_id.is_(None)).scalar()
    return {
        "period_hours": 24,
        "events": recent.count(),
        "failed_logins": recent.filter(SecurityEvent.event_type == "LOGIN_FAILED").count(),
        "high_risk_events": recent.filter(SecurityEvent.risk_level == "HIGH").count(),
        "open_high_risk_alerts": open_high or 0,
    }


@router.get("/events")
def events(
    username: str | None = Query(default=None, max_length=128),
    risk: Literal["LOW", "MEDIUM", "HIGH"] | None = None,
    event_type: str | None = Query(default=None, max_length=80, pattern="^[A-Z0-9_]+$"),
    before_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    _: AuthSession = Depends(require_monitoring_admin), db: Session = Depends(get_db),
):
    query = db.query(SecurityEvent)
    if username:
        query = query.filter(SecurityEvent.username == username.strip())
    if risk:
        query = query.filter(SecurityEvent.risk_level == risk)
    if event_type:
        query = query.filter(SecurityEvent.event_type == event_type)
    if before_id:
        query = query.filter(SecurityEvent.id < before_id)
    rows = query.order_by(SecurityEvent.id.desc()).limit(limit + 1).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    return {"events": [event_data(row) for row in rows],
            "next_before_id": rows[-1].id if has_more else None}


@router.get("/alerts")
def alerts(
    before_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    _: AuthSession = Depends(require_monitoring_admin), db: Session = Depends(get_db),
):
    query = db.query(SecurityEvent, SecurityAlertReview).outerjoin(
        SecurityAlertReview, SecurityAlertReview.event_id == SecurityEvent.id,
    ).filter(SecurityEvent.risk_level == "HIGH")
    if before_id:
        query = query.filter(SecurityEvent.id < before_id)
    rows = query.order_by(SecurityEvent.id.desc()).limit(limit + 1).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    return {"alerts": [{**event_data(event), "review": ({
        "reviewed_by": review.reviewed_by, "note": review.note,
        "reviewed_at": utc(review.reviewed_at).isoformat(),
    } if review else None)} for event, review in rows],
            "next_before_id": rows[-1][0].id if has_more else None}


@router.post("/alerts/{event_id}/review")
def review_alert(
    event_id: int, payload: ReviewRequest, request: Request,
    session: AuthSession = Depends(require_monitoring_admin), db: Session = Depends(get_db),
):
    note = payload.note.strip()
    if len(note) < 8:
        raise HTTPException(status_code=422, detail="Review note needs at least eight characters.")
    event = db.get(SecurityEvent, event_id)
    if not event or event.risk_level != "HIGH":
        raise HTTPException(status_code=404, detail="High-risk alert not found.")
    if db.get(SecurityAlertReview, event_id):
        raise HTTPException(status_code=409, detail="This alert was already reviewed.")
    db.add(SecurityAlertReview(event_id=event_id, reviewed_by=session.username, note=note,
                               reviewed_at=datetime.now(timezone.utc)))
    record_security_event(
        db, event_type="SECURITY_ALERT_REVIEWED", username=session.username,
        ip_address=request.client.host if request.client else None,
        details={"event_id": event_id},
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This alert was already reviewed.")
    return {"reviewed": True, "event_id": event_id}
