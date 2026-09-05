"""Gmail OAuth + inbox reading. Tokens are stored in IntegrationState under key 'gmail_token'."""
import base64
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from ..config import settings
from ..models import IntegrationState

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_KEY = "gmail_token"


def _client_config() -> dict:
    return {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }


def auth_url() -> str:
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES, redirect_uri=settings.google_redirect_uri)
    url, _ = flow.authorization_url(access_type="offline", prompt="consent", include_granted_scopes="true")
    return url


def exchange_code(db: Session, code: str) -> None:
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES, redirect_uri=settings.google_redirect_uri)
    flow.fetch_token(code=code)
    _save(db, flow.credentials)


def _save(db: Session, creds: Credentials) -> None:
    row = db.get(IntegrationState, TOKEN_KEY) or IntegrationState(key=TOKEN_KEY)
    row.value = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes or SCOPES),
    }
    db.add(row)
    db.commit()


def is_connected(db: Session) -> bool:
    row = db.get(IntegrationState, TOKEN_KEY)
    return bool(row and row.value and row.value.get("refresh_token"))


def disconnect(db: Session) -> None:
    row = db.get(IntegrationState, TOKEN_KEY)
    if row:
        db.delete(row)
        db.commit()


def _creds(db: Session) -> Credentials:
    row = db.get(IntegrationState, TOKEN_KEY)
    if not row or not row.value:
        raise RuntimeError("Gmail not connected")
    creds = Credentials(**row.value)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save(db, creds)
    return creds


def _decode_body(payload: dict) -> str:
    """Prefer text/plain; fall back to stripping html. Recurses into multipart."""
    mime = payload.get("mimeType", "")
    data = payload.get("body", {}).get("data")
    if data and mime.startswith("text/plain"):
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    for part in payload.get("parts", []) or []:
        text = _decode_body(part)
        if text:
            return text
    if data and mime.startswith("text/html"):
        from bs4 import BeautifulSoup
        html = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        return BeautifulSoup(html, "html.parser").get_text("\n")
    return ""


def fetch_recent(db: Session, since_days: int = 2, max_results: int = 100) -> list[dict]:
    """Return recent inbox messages as dicts: gmail_id, thread_id, sender, subject, body, received_at."""
    service = build("gmail", "v1", credentials=_creds(db), cache_discovery=False)
    after = int((datetime.utcnow() - timedelta(days=since_days)).timestamp())
    query = f"after:{after} -category:promotions -category:social"
    resp = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    out = []
    for ref in resp.get("messages", []):
        msg = service.users().messages().get(userId="me", id=ref["id"], format="full").execute()
        headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
        out.append({
            "gmail_id": msg["id"],
            "thread_id": msg.get("threadId"),
            "sender": headers.get("from", ""),
            "subject": headers.get("subject", ""),
            "snippet": msg.get("snippet", ""),
            "body": _decode_body(msg["payload"]) or msg.get("snippet", ""),
            "received_at": datetime.utcfromtimestamp(int(msg["internalDate"]) / 1000),
        })
    return out
