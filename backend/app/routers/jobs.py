from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import DiscoveredJob
from ..schemas import DiscoveredJobOut

router = APIRouter(prefix="/api/jobs", tags=["discover"])


@router.get("", response_model=list[DiscoveredJobOut])
def list_jobs(min_score: float = 0, include_dismissed: bool = False, db: Session = Depends(get_db)):
    q = select(DiscoveredJob)
    if min_score > 0:
        q = q.where(DiscoveredJob.match_score >= min_score)  # at 0, unscored (NULL) jobs show too
    if not include_dismissed:
        q = q.where((DiscoveredJob.verdict.is_(None)) | (DiscoveredJob.verdict == "saved"))
    return list(db.scalars(q.order_by(DiscoveredJob.match_score.desc(), DiscoveredJob.found_at.desc()).limit(200)))


@router.post("/{job_id}/dismiss", response_model=DiscoveredJobOut)
def dismiss(job_id: int, db: Session = Depends(get_db)):
    j = db.get(DiscoveredJob, job_id)
    if not j:
        raise HTTPException(404)
    j.verdict = "dismissed"
    db.commit()
    return j
