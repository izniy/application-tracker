from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Alert, Application, ApplicationStatus, StatusEvent
from ..schemas import AlertOut

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def list_alerts(include_dismissed: bool = False, db: Session = Depends(get_db)):
    q = select(Alert).order_by(Alert.urgency.desc(), Alert.created_at.desc())
    if not include_dismissed:
        q = q.where(Alert.dismissed.is_(False))
    return list(db.scalars(q.limit(200)))


@router.post("/{alert_id}/read", response_model=AlertOut)
def mark_read(alert_id: int, db: Session = Depends(get_db)):
    a = db.get(Alert, alert_id)
    if not a:
        raise HTTPException(404)
    a.read = True
    db.commit()
    return a


@router.post("/{alert_id}/dismiss", response_model=AlertOut)
def dismiss(alert_id: int, db: Session = Depends(get_db)):
    a = db.get(Alert, alert_id)
    if not a:
        raise HTTPException(404)
    a.dismissed = a.read = True
    db.commit()
    return a


@router.post("/{alert_id}/apply-status", response_model=AlertOut)
def apply_suggested_status(alert_id: int, db: Session = Depends(get_db)):
    """One-click: accept the status the email classifier proposed."""
    a = db.get(Alert, alert_id)
    if not a or not a.application_id or not a.suggested_status:
        raise HTTPException(400, "Nothing to apply")
    app = db.get(Application, a.application_id)
    new = ApplicationStatus(a.suggested_status)
    if app.status != new:
        db.add(StatusEvent(application_id=app.id, from_status=app.status.value, to_status=new.value,
                           reason=a.title, source="email"))
        app.status = new
    a.suggested_status = None
    a.read = True
    db.commit()
    return a


@router.post("/read-all")
def read_all(db: Session = Depends(get_db)):
    for a in db.scalars(select(Alert).where(Alert.read.is_(False))):
        a.read = True
    db.commit()
    return {"ok": True}
