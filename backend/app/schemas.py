from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer

from .models import AlertKind, ApplicationStatus


def _utc_z(dt: datetime) -> str:
    """DB datetimes are naive UTC; emit them with an explicit Z so browsers parse them correctly."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


UTCDateTime = Annotated[datetime, PlainSerializer(_utc_z, when_used="json")]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- Applications ----
class ApplicationCreate(BaseModel):
    company: str
    role: str
    location: str | None = None
    url: str | None = None
    source: str | None = None
    status: ApplicationStatus = ApplicationStatus.applied
    applied_at: datetime | None = None
    next_action: str | None = None
    next_action_at: datetime | None = None
    notes: str | None = None
    job_description: str | None = None
    company_domains: list[str] | None = None


class ApplicationUpdate(BaseModel):
    company: str | None = None
    role: str | None = None
    location: str | None = None
    url: str | None = None
    source: str | None = None
    status: ApplicationStatus | None = None
    status_reason: str | None = None
    applied_at: datetime | None = None
    next_action: str | None = None
    next_action_at: datetime | None = None
    notes: str | None = None
    job_description: str | None = None
    company_domains: list[str] | None = None


class StatusEventOut(ORM):
    id: int
    from_status: str | None
    to_status: str
    reason: str | None
    source: str
    created_at: UTCDateTime


class ApplicationOut(ORM):
    id: int
    company: str
    role: str
    location: str | None
    url: str | None
    source: str | None
    status: ApplicationStatus
    applied_at: UTCDateTime | None
    next_action: str | None
    next_action_at: UTCDateTime | None
    notes: str | None
    job_description: str | None
    company_domains: list[str] | None
    created_at: UTCDateTime
    updated_at: UTCDateTime
    events: list[StatusEventOut] = []


# ---- Alerts ----
class AlertOut(ORM):
    id: int
    kind: AlertKind
    title: str
    body: str | None
    application_id: int | None
    email_id: int | None
    suggested_status: str | None
    urgency: int
    read: bool
    dismissed: bool
    created_at: UTCDateTime


# ---- Discovered jobs ----
class DiscoveredJobOut(ORM):
    id: int
    external_id: str
    source: str
    company: str
    role: str
    location: str | None
    url: str
    description: str | None
    posted_at: UTCDateTime | None
    match_score: float | None
    match_reason: str | None
    verdict: str | None
    found_at: UTCDateTime


# ---- Profile ----
class ProfileUpdate(BaseModel):
    name: str | None = None
    headline: str | None = None
    location: str | None = None
    target_roles: list[str] | None = None
    target_locations: list[str] | None = None
    skills: list[str] | None = None
    seniority: str | None = None
    availability: str | None = None
    preferences: str | None = None


class ProfileOut(ORM):
    id: int
    name: str | None
    headline: str | None
    location: str | None
    target_roles: list[str] | None
    target_locations: list[str] | None
    skills: list[str] | None
    seniority: str | None
    availability: str | None
    preferences: str | None
    resume_filename: str | None
    resume_text: str | None
    llm_summary: str | None
    updated_at: UTCDateTime


# ---- Job runs ----
class JobRunOut(ORM):
    job: str
    started_at: UTCDateTime
    finished_at: UTCDateTime | None
    ok: bool
    summary: str | None


# ---- Dashboard ----
class DashboardOut(BaseModel):
    counts_by_status: dict[str, int]
    active: int
    response_rate: float  # % of applied that progressed past 'applied'
    unread_alerts: int
    due_soon: list[ApplicationOut]
    recent_alerts: list[AlertOut]
    top_matches: list[DiscoveredJobOut]
    last_runs: dict[str, UTCDateTime | None]
    email_connected: bool
    profile_ready: bool
