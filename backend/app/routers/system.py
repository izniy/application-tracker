"""Dashboard aggregate + manual triggers for the automated jobs."""
from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import SessionLocal, get_db
from ..models import Alert, Application, ApplicationStatus, DiscoveredJob, JobRunLog, Profile
from ..schemas import DashboardOut, JobRunOut
from ..services import gmail, pipelines
from ..services.pipelines import ACTIVE

router = APIRouter(prefix="/api/system", tags=["system"])

JOBS = {"email_scan": pipelines.email_scan, "job_scan": pipelines.job_scan, "deadline_check": pipelines.deadline_check}


def _last_run(db: Session, job: str) -> datetime | None:
    return db.scalar(select(JobRunLog.finished_at).where(JobRunLog.job == job, JobRunLog.ok.is_(True))
                     .order_by(JobRunLog.started_at.desc()).limit(1))


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db)):
    counts = {s.value: 0 for s in ApplicationStatus}
    for status, n in db.execute(select(Application.status, func.count()).group_by(Application.status)):
        counts[status.value] = n
    applied_total = sum(v for k, v in counts.items() if k != "saved")
    progressed = counts["online_assessment"] + counts["interviewing"] + counts["offer"]
    profile = db.get(Profile, 1)
    return DashboardOut(
        counts_by_status=counts,
        active=sum(counts[s.value] for s in ACTIVE if s != ApplicationStatus.saved),
        response_rate=round(100 * progressed / applied_total, 1) if applied_total else 0.0,
        unread_alerts=db.scalar(select(func.count()).select_from(Alert).where(Alert.read.is_(False), Alert.dismissed.is_(False))) or 0,
        due_soon=list(db.scalars(select(Application).where(Application.next_action_at.is_not(None), Application.status.in_(ACTIVE))
                                 .order_by(Application.next_action_at).limit(5))),
        recent_alerts=list(db.scalars(select(Alert).where(Alert.dismissed.is_(False)).order_by(Alert.created_at.desc()).limit(6))),
        top_matches=list(db.scalars(select(DiscoveredJob).where(DiscoveredJob.verdict.is_(None), DiscoveredJob.found_at >= datetime.utcnow() - timedelta(days=7))
                                    .order_by(DiscoveredJob.match_score.desc()).limit(5))),
        last_runs={k: _last_run(db, k) for k in JOBS},
        email_connected=gmail.is_connected(db),
        profile_ready=bool(profile and profile.llm_summary),
    )


@router.post("/run/{job}")
def run_job(job: str, background: BackgroundTasks):
    if job not in JOBS:
        raise HTTPException(404, f"Unknown job. Choose one of {list(JOBS)}")

    def task():
        db = SessionLocal()
        try:
            JOBS[job](db)
        finally:
            db.close()

    background.add_task(task)
    return {"queued": job}


@router.get("/runs", response_model=list[JobRunOut])
def runs(db: Session = Depends(get_db)):
    return list(db.scalars(select(JobRunLog).order_by(JobRunLog.started_at.desc()).limit(30)))
