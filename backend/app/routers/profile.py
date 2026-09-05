from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Profile
from ..schemas import ProfileOut, ProfileUpdate
from ..services import profile_summary, resume_parser

router = APIRouter(prefix="/api/profile", tags=["profile"])


def _get_or_create(db: Session) -> Profile:
    p = db.get(Profile, 1)
    if not p:
        p = Profile(id=1)
        db.add(p)
        db.commit()
        db.refresh(p)
    return p


@router.get("", response_model=ProfileOut)
def get_profile(db: Session = Depends(get_db)):
    return _get_or_create(db)


@router.put("", response_model=ProfileOut)
def update_profile(payload: ProfileUpdate, db: Session = Depends(get_db)):
    p = _get_or_create(db)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p


@router.post("/resume", response_model=ProfileOut)
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith((".pdf", ".docx", ".txt", ".md")):
        raise HTTPException(400, "Upload a PDF, DOCX, TXT or MD file")
    p = _get_or_create(db)
    p.resume_text = resume_parser.extract_text(file.filename, await file.read())
    p.resume_filename = file.filename
    db.commit()
    db.refresh(p)
    return p


@router.post("/summarise", response_model=ProfileOut)
def summarise(db: Session = Depends(get_db)):
    """Regenerate the LLM profile summary used by the matcher."""
    p = _get_or_create(db)
    p.llm_summary = profile_summary.build_summary(p)
    db.commit()
    db.refresh(p)
    return p
