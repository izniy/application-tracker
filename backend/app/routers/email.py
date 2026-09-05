import logging

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..services import gmail

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/email", tags=["email"])


@router.get("/status")
def status(db: Session = Depends(get_db)):
    return {"connected": gmail.is_connected(db), "configured": bool(settings.google_client_id)}


@router.get("/oauth/start")
def oauth_start():
    return RedirectResponse(gmail.auth_url())


@router.get("/oauth/callback")
def oauth_callback(code: str | None = None, error: str | None = None, db: Session = Depends(get_db)):
    if error or not code:
        # User denied consent or Google reported an error — land back in Settings, not on a traceback.
        return RedirectResponse(f"{settings.frontend_origin}/settings?email=error")
    try:
        gmail.exchange_code(db, code)
    except Exception:
        log.exception("Gmail OAuth code exchange failed")
        return RedirectResponse(f"{settings.frontend_origin}/settings?email=error")
    return RedirectResponse(f"{settings.frontend_origin}/settings?email=connected")


@router.post("/disconnect")
def disconnect(db: Session = Depends(get_db)):
    gmail.disconnect(db)
    return {"connected": False}
