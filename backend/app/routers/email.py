from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..services import gmail

router = APIRouter(prefix="/api/email", tags=["email"])


@router.get("/status")
def status(db: Session = Depends(get_db)):
    return {"connected": gmail.is_connected(db), "configured": bool(settings.google_client_id)}


@router.get("/oauth/start")
def oauth_start():
    return RedirectResponse(gmail.auth_url())


@router.get("/oauth/callback")
def oauth_callback(code: str, db: Session = Depends(get_db)):
    gmail.exchange_code(db, code)
    return RedirectResponse(f"{settings.frontend_origin}/settings?email=connected")


@router.post("/disconnect")
def disconnect(db: Session = Depends(get_db)):
    gmail.disconnect(db)
    return {"connected": False}
