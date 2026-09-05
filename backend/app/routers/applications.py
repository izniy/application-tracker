from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Application, ApplicationStatus, DiscoveredJob, StatusEvent
from ..schemas import ApplicationCreate, ApplicationOut, ApplicationUpdate

router = APIRouter(prefix="/api/applications", tags=["applications"])


@router.get("", response_model=list[ApplicationOut])
def list_applications(status: ApplicationStatus | None = None, db: Session = Depends(get_db)):
    q = select(Application).order_by(Application.updated_at.desc())
    if status:
        q = q.where(Application.status == status)
    return list(db.scalars(q))


@router.post("", response_model=ApplicationOut, status_code=201)
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db)):
    app = Application(**payload.model_dump())
    if app.status == ApplicationStatus.applied and not app.applied_at:
        app.applied_at = datetime.utcnow()
    db.add(app)
    db.flush()
    db.add(StatusEvent(application_id=app.id, from_status=None, to_status=app.status.value, source="manual"))
    db.commit()
    db.refresh(app)
    return app


@router.post("/from-discovered/{job_id}", response_model=ApplicationOut, status_code=201)
def create_from_discovered(job_id: int, db: Session = Depends(get_db)):
    job = db.get(DiscoveredJob, job_id)
    if not job:
        raise HTTPException(404, "Discovered job not found")
    app = Application(company=job.company, role=job.role, location=job.location, url=job.url,
                      source=f"orbit:{job.source}", status=ApplicationStatus.saved, job_description=job.description)
    db.add(app)
    db.flush()
    db.add(StatusEvent(application_id=app.id, to_status="saved", source="manual"))
    job.verdict = "saved"
    db.commit()
    db.refresh(app)
    return app


@router.get("/{app_id}", response_model=ApplicationOut)
def get_application(app_id: int, db: Session = Depends(get_db)):
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(404)
    return app


@router.patch("/{app_id}", response_model=ApplicationOut)
def update_application(app_id: int, payload: ApplicationUpdate, db: Session = Depends(get_db)):
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(404)
    data = payload.model_dump(exclude_unset=True)
    reason = data.pop("status_reason", None)
    new_status = data.get("status")
    if new_status and new_status != app.status:
        db.add(StatusEvent(application_id=app.id, from_status=app.status.value, to_status=new_status.value,
                           reason=reason, source="manual"))
        if new_status == ApplicationStatus.applied and not app.applied_at:
            app.applied_at = datetime.utcnow()
    for k, v in data.items():
        setattr(app, k, v)
    db.commit()
    db.refresh(app)
    return app


@router.delete("/{app_id}", status_code=204)
def delete_application(app_id: int, db: Session = Depends(get_db)):
    app = db.get(Application, app_id)
    if app:
        db.delete(app)
        db.commit()
