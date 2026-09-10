"""The three automated jobs. Each is idempotent and safe to re-run manually from the UI."""
import logging
import re
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Alert, AlertKind, Application, ApplicationStatus, DiscoveredJob, Email, JobRunLog, Profile, StatusEvent
from . import email_classifier, gmail, matcher
from .scraper.registry import active_sources

log = logging.getLogger(__name__)

ACTIVE = [ApplicationStatus.saved, ApplicationStatus.applied, ApplicationStatus.online_assessment,
          ApplicationStatus.interviewing, ApplicationStatus.offer]


def _run(db: Session, name: str, fn) -> JobRunLog:
    run = JobRunLog(job=name)
    db.add(run)
    db.commit()
    try:
        run.summary = fn()
        run.ok = True
    except Exception as e:  # noqa: BLE001
        log.exception("%s failed", name)
        db.rollback()  # the failure may have poisoned the transaction; recover or the log write below dies too
        run.ok = False
        run.summary = f"{type(e).__name__}: {e}"[:500]
    run.finished_at = datetime.utcnow()
    db.commit()
    return run


# ------------------------------------------------------------------ email scan
KIND_FOR_CATEGORY = {
    "online_assessment": AlertKind.assessment,
    "interview_invite": AlertKind.interview,
    "interview_followup": AlertKind.follow_up,
    "offer": AlertKind.status_update,
    "rejection": AlertKind.status_update,
    "application_received": AlertKind.status_update,
    "recruiter_outreach": AlertKind.new_company,
    "other_job_related": AlertKind.follow_up,
}

# Cheap pre-filter so we don't send every newsletter to the LLM.
JOB_HINTS = re.compile(
    r"applicat|interview|assessment|hackerrank|codility|recruit|talent|position|role|offer|"
    r"candidate|hiring|career|opportunit|next step|greenhouse|lever|workday|ashby|myworkday",
    re.I,
)


def _domain(sender: str) -> str | None:
    m = re.search(r"@([\w.-]+)", sender)
    return m.group(1).lower() if m else None


# Domains that identify a mail platform or ATS, not the employer — learning one of these
# for auto-linking would attach every company's mail on that platform to one application.
SHARED_MAIL_DOMAINS = (
    "gmail.com", "outlook.com", "yahoo.com", "googlemail.com",
    "greenhouse-mail.io", "greenhouse.io", "lever.co", "myworkday.com", "myworkdayjobs.com",
    "workday.com", "ashbyhq.com", "smartrecruiters.com", "icims.com", "jobvite.com",
    "taleo.net", "oraclecloud.com", "successfactors.com", "bamboohr.com",
    "hackerrank.com", "codility.com", "codesignal.com", "hirevue.com", "linkedin.com",
)


def _learnable_domain(sender: str) -> str | None:
    d = _domain(sender)
    if d and not any(d == s or d.endswith("." + s) for s in SHARED_MAIL_DOMAINS):
        return d
    return None


def _match_by_domain(db: Session, sender: str) -> Application | None:
    d = _domain(sender)
    if not d:
        return None
    for app in db.scalars(select(Application)):
        for dom in app.company_domains or []:
            if d.endswith(dom.lower()):
                return app
    return None


def _gmail_reconnect_alert(db: Session) -> None:
    """One undismissed reconnect alert at a time; scans keep failing until the user acts."""
    exists = db.scalar(select(Alert).where(Alert.kind == AlertKind.system, Alert.dismissed.is_(False),
                                           Alert.title.contains("Gmail")))
    if not exists:
        db.add(Alert(kind=AlertKind.system, title="Gmail connection expired — reconnect in Settings",
                     body="Google stopped accepting Orbit's token, so inbox scans are paused. "
                          "Open Settings and connect Gmail again.", urgency=3))
    db.commit()


def email_scan(db: Session) -> JobRunLog:
    def work():
        if not gmail.is_connected(db):
            return "Gmail not connected — skipped"
        tracked = list(db.scalars(select(Application).where(Application.status.in_(ACTIVE))))
        try:
            messages = gmail.fetch_recent(db, since_days=2)
        except gmail.GmailAuthError:
            _gmail_reconnect_alert(db)
            raise
        # Oldest first, and only the newest unseen message per thread gets classified —
        # earlier messages in the same conversation are recorded but never alert.
        messages.sort(key=lambda m: m["received_at"] or datetime.min)
        newest_in_thread = {m["thread_id"] or m["gmail_id"]: m["gmail_id"] for m in messages}
        seen = 0
        created = 0
        for m in messages:
            if db.scalar(select(Email).where(Email.gmail_id == m["gmail_id"])):
                continue
            seen += 1
            if newest_in_thread[m["thread_id"] or m["gmail_id"]] != m["gmail_id"]:
                db.add(Email(gmail_id=m["gmail_id"], thread_id=m["thread_id"], sender=m["sender"],
                             subject=m["subject"], snippet=m["snippet"], received_at=m["received_at"],
                             classification={"category": "superseded_in_thread"}))
                continue
            text = f"{m['subject']} {m['snippet']} {m['sender']}"
            if not JOB_HINTS.search(text) and not _match_by_domain(db, m["sender"]):
                db.add(Email(gmail_id=m["gmail_id"], thread_id=m["thread_id"], sender=m["sender"],
                             subject=m["subject"], snippet=m["snippet"], received_at=m["received_at"],
                             classification={"category": "prefiltered_out"}))
                continue

            c = email_classifier.classify(m["sender"], m["subject"], m["body"], tracked)
            app = None
            try:
                if c.get("application_id") is not None:
                    app = db.get(Application, int(c["application_id"]))
            except (TypeError, ValueError):
                app = None
            app = app or _match_by_domain(db, m["sender"])

            email = Email(gmail_id=m["gmail_id"], thread_id=m["thread_id"], sender=m["sender"],
                          subject=m["subject"], snippet=m["snippet"], received_at=m["received_at"],
                          classification=c, application_id=app.id if app else None)
            db.add(email)
            db.flush()

            cat = c.get("category", "not_job_related")
            if cat == "not_job_related":
                continue

            # Learn the sender domain so future mail auto-links without an LLM call.
            if app and (d := _learnable_domain(m["sender"])) and not any(d.endswith(x) for x in (app.company_domains or [])):
                app.company_domains = [*(app.company_domains or []), d]

            # A newer message in a thread supersedes any alert an older one raised.
            if m["thread_id"]:
                stale = db.scalars(select(Alert).join(Email, Alert.email_id == Email.id)
                                   .where(Email.thread_id == m["thread_id"], Alert.dismissed.is_(False)))
                for a in stale:
                    a.dismissed = a.read = True

            kind = KIND_FOR_CATEGORY.get(cat, AlertKind.follow_up)
            if cat == "recruiter_outreach" and app:
                kind = AlertKind.follow_up
            title = c.get("summary") or m["subject"] or "Job-related email"
            company = app.company if app else (c.get("company") or _domain(m["sender"]) or "Unknown company")
            db.add(Alert(
                kind=kind,
                title=f"{company}: {title}",
                body=c.get("action") or m["snippet"],
                application_id=app.id if app else None,
                email_id=email.id,
                suggested_status=c.get("suggested_status") if app and c.get("suggested_status") != app.status.value else None,
                urgency=int(c.get("urgency") or 1),
            ))
            created += 1

            # Deadlines mentioned in email become the app's next action if it has none.
            if app and c.get("deadline") and not app.next_action_at:
                try:
                    app.next_action_at = datetime.fromisoformat(c["deadline"])
                    app.next_action = c.get("action") or title
                except ValueError:
                    pass
        db.commit()
        return f"{len(messages)} fetched, {seen} new, {created} alerts"

    return _run(db, "email_scan", work)


def track_alert(db: Session, alert: Alert) -> Application:
    """One click on an untracked signal: create the application the email implies,
    link the alert and email to it, and learn the sender domain for auto-linking."""
    email = db.get(Email, alert.email_id) if alert.email_id else None
    c = (email.classification if email else None) or {}
    company = c.get("company") or alert.title.split(":")[0].strip() or "Unknown company"
    status = ApplicationStatus(email_classifier.STATUS_FOR_CATEGORY.get(c.get("category", ""), "applied"))
    domain = _learnable_domain(email.sender) if email else None
    app = Application(
        company=company,
        role=c.get("role") or "Role from email",
        status=status,
        applied_at=(email.received_at if email else None) or datetime.utcnow(),
        company_domains=[domain] if domain else None,
    )
    db.add(app)
    db.flush()
    db.add(StatusEvent(application_id=app.id, to_status=status.value, reason=alert.title, source="email"))
    alert.application_id = app.id
    alert.read = True
    if email:
        email.application_id = app.id
    db.commit()
    return app


# ------------------------------------------------------------------ job discovery
def job_scan(db: Session) -> JobRunLog:
    def work():
        profile = db.get(Profile, 1)
        if not profile or not (profile.target_roles or profile.llm_summary):
            return "Profile incomplete — skipped"
        applied = list(db.scalars(select(Application).order_by(Application.created_at.desc())))
        queries = list(dict.fromkeys([*(profile.target_roles or []), *[a.role for a in applied[:5]]]))
        locations = profile.target_locations or []

        new_jobs: list[DiscoveredJob] = []
        seen_ids: set[str] = set()  # sources return the same posting for several queries
        for source in active_sources():
            try:
                for raw in source.search(queries, locations):
                    if raw.external_id in seen_ids:
                        continue
                    seen_ids.add(raw.external_id)
                    if db.scalar(select(DiscoveredJob).where(DiscoveredJob.external_id == raw.external_id)):
                        continue
                    # skip companies already applied to for the same role
                    if any(a.company.lower() == raw.company.lower() and a.role.lower() == raw.role.lower() for a in applied):
                        continue
                    job = DiscoveredJob(external_id=raw.external_id, source=raw.source, company=raw.company,
                                        role=raw.role, location=raw.location, url=raw.url,
                                        description=raw.description, posted_at=raw.posted_at)
                    db.add(job)
                    new_jobs.append(job)
            except Exception:  # noqa: BLE001
                log.exception("source %s failed", source.name)
        db.commit()  # persist finds before scoring — a failed scoring pass loses nothing

        # Score new jobs plus any recent ones a previous run failed to score.
        # Batches of 15 keep prompts small; commit per batch so results appear as they land.
        verdicts = list(db.scalars(select(DiscoveredJob).where(DiscoveredJob.verdict.is_not(None))
                                   .order_by(DiscoveredJob.found_at.desc()).limit(20)))
        unscored = list(db.scalars(select(DiscoveredJob).where(
            DiscoveredJob.match_score.is_(None),
            DiscoveredJob.found_at >= datetime.utcnow() - timedelta(days=7))))
        for i in range(0, len(unscored), 15):
            batch = unscored[i:i + 15]
            for jid, s in matcher.score_batch(profile, applied, batch, verdicts).items():
                job = db.get(DiscoveredJob, jid)
                if job:
                    job.match_score, job.match_reason = s["score"], s["reason"]
            db.commit()

        strong = [j for j in unscored if (j.match_score or 0) >= 80]
        for j in strong[:5]:
            db.add(Alert(kind=AlertKind.discovery, title=f"Strong match: {j.role} at {j.company}",
                         body=j.match_reason, urgency=2))
        db.commit()
        return f"{len(new_jobs)} new jobs from {len(active_sources())} sources, {len(unscored)} scored, {len(strong)} strong matches"

    return _run(db, "job_scan", work)


# ------------------------------------------------------------------ deadlines
def deadline_check(db: Session) -> JobRunLog:
    def work():
        soon = datetime.utcnow() + timedelta(days=2)
        n = 0
        for app in db.scalars(select(Application).where(Application.next_action_at <= soon,
                                                         Application.status.in_(ACTIVE))):
            exists = db.scalar(select(Alert).where(Alert.application_id == app.id, Alert.kind == AlertKind.deadline,
                                                   Alert.dismissed.is_(False), Alert.created_at >= datetime.utcnow() - timedelta(days=1)))
            if exists:
                continue
            db.add(Alert(kind=AlertKind.deadline, title=f"{app.company}: {app.next_action or 'action due'}",
                         body=f"Due {app.next_action_at:%a %d %b}", application_id=app.id, urgency=3))
            n += 1
        # Flag ghosted: applied > 30 days, no movement.
        stale = datetime.utcnow() - timedelta(days=30)
        for app in db.scalars(select(Application).where(Application.status == ApplicationStatus.applied,
                                                         Application.updated_at < stale)):
            app.status = ApplicationStatus.ghosted
            db.add(StatusEvent(application_id=app.id, from_status="applied", to_status="ghosted",
                               reason="No response in 30 days", source="system"))
        db.commit()
        return f"{n} deadline alerts"

    return _run(db, "deadline_check", work)
