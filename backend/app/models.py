import enum
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class ApplicationStatus(str, enum.Enum):
    saved = "saved"
    applied = "applied"
    online_assessment = "online_assessment"
    interviewing = "interviewing"
    offer = "offer"
    rejected = "rejected"
    withdrawn = "withdrawn"
    ghosted = "ghosted"


STATUS_ORDER = [s.value for s in ApplicationStatus]


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    company: Mapped[str] = mapped_column(String(200), index=True)
    role: Mapped[str] = mapped_column(String(200))
    location: Mapped[str | None] = mapped_column(String(200))
    url: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(100))  # linkedin, referral, orbit-discover...
    status: Mapped[ApplicationStatus] = mapped_column(Enum(ApplicationStatus), default=ApplicationStatus.applied, index=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime)
    next_action: Mapped[str | None] = mapped_column(Text)  # e.g. "OA due 12 Sep"
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime)
    notes: Mapped[str | None] = mapped_column(Text)
    job_description: Mapped[str | None] = mapped_column(Text)
    company_domains: Mapped[list | None] = mapped_column(JSON)  # emails from these map here
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    events: Mapped[list["StatusEvent"]] = relationship(back_populates="application", cascade="all, delete-orphan")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="application")


class StatusEvent(Base):
    """Timeline of status changes, including ones inferred from email."""
    __tablename__ = "status_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"))
    from_status: Mapped[str | None] = mapped_column(String(50))
    to_status: Mapped[str] = mapped_column(String(50))
    reason: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(50), default="manual")  # manual | email
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    application: Mapped[Application] = relationship(back_populates="events")


class AlertKind(str, enum.Enum):
    status_update = "status_update"      # email indicates status changed
    interview = "interview"              # interview invite / scheduling
    assessment = "assessment"            # OA link
    follow_up = "follow_up"              # recruiter asking for something
    new_company = "new_company"          # email from a company not being tracked
    deadline = "deadline"                # next_action_at approaching
    discovery = "discovery"              # strong new job match
    system = "system"                    # Orbit needs the user's attention (e.g. reconnect Gmail)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[AlertKind] = mapped_column(Enum(AlertKind), index=True)
    title: Mapped[str] = mapped_column(String(300))
    body: Mapped[str | None] = mapped_column(Text)
    application_id: Mapped[int | None] = mapped_column(ForeignKey("applications.id"), nullable=True)
    email_id: Mapped[int | None] = mapped_column(ForeignKey("emails.id"), nullable=True)
    suggested_status: Mapped[str | None] = mapped_column(String(50))  # LLM proposal; user confirms
    urgency: Mapped[int] = mapped_column(Integer, default=1)  # 1 low .. 3 high
    read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    application: Mapped[Application | None] = relationship(back_populates="alerts")


class Email(Base):
    """Stored copy of job-related emails we've already processed (dedup + audit)."""
    __tablename__ = "emails"

    id: Mapped[int] = mapped_column(primary_key=True)
    gmail_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    thread_id: Mapped[str | None] = mapped_column(String(100))
    sender: Mapped[str] = mapped_column(String(300))
    subject: Mapped[str | None] = mapped_column(Text)
    snippet: Mapped[str | None] = mapped_column(Text)
    received_at: Mapped[datetime | None] = mapped_column(DateTime)
    classification: Mapped[dict | None] = mapped_column(JSON)  # raw LLM output
    application_id: Mapped[int | None] = mapped_column(ForeignKey("applications.id"), nullable=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DiscoveredJob(Base):
    __tablename__ = "discovered_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(300), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(100))
    company: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(300))
    location: Mapped[str | None] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime)
    match_score: Mapped[float | None] = mapped_column(Float, index=True)  # 0-100
    match_reason: Mapped[str | None] = mapped_column(Text)
    verdict: Mapped[str | None] = mapped_column(String(20))  # null | saved | dismissed | applied
    found_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class Profile(Base):
    """Single-row table: the user's profile the LLM reasons over."""
    __tablename__ = "profile"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    name: Mapped[str | None] = mapped_column(String(200))
    headline: Mapped[str | None] = mapped_column(String(300))
    location: Mapped[str | None] = mapped_column(String(200))
    target_roles: Mapped[list | None] = mapped_column(JSON)       # ["Software Engineer Intern", ...]
    target_levels: Mapped[list | None] = mapped_column(JSON)      # ["Internship", "New Grad", ...]
    target_locations: Mapped[list | None] = mapped_column(JSON)   # ["Singapore", "Remote"]
    skills: Mapped[list | None] = mapped_column(JSON)             # tech stack: languages, frameworks, infra
    seniority: Mapped[str | None] = mapped_column(String(50))     # intern | new_grad | mid | senior
    availability: Mapped[str | None] = mapped_column(String(200)) # "Feb–May 2027 internship; FT from Jun 2027"
    preferences: Mapped[str | None] = mapped_column(Text)         # free text: what excites you, dealbreakers
    resume_text: Mapped[str | None] = mapped_column(Text)
    resume_filename: Mapped[str | None] = mapped_column(String(300))
    llm_summary: Mapped[str | None] = mapped_column(Text)         # LLM-condensed profile used in prompts
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class IntegrationState(Base):
    """Key/value store for OAuth tokens, last-sync cursors, etc."""
    __tablename__ = "integration_state"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict | None] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class JobRunLog(Base):
    __tablename__ = "job_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    job: Mapped[str] = mapped_column(String(50))  # email_scan | job_scan | deadline_check
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    summary: Mapped[str | None] = mapped_column(Text)
