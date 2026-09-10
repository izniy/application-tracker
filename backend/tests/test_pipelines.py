"""Pipeline behavior with Gmail and the LLM mocked out — runs offline."""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Alert, Application, ApplicationStatus, DiscoveredJob, Email
from app.services import pipelines
from app.services.scraper.base import JobSource, RawJob


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _msg(gmail_id: str, thread_id: str, minutes_ago: int, subject: str, sender: str = "Recruiter <r@stripe.com>"):
    return {"gmail_id": gmail_id, "thread_id": thread_id, "sender": sender, "subject": subject,
            "snippet": subject, "body": subject, "received_at": datetime.utcnow() - timedelta(minutes=minutes_ago)}


def _wire_gmail(monkeypatch, messages):
    monkeypatch.setattr(pipelines.gmail, "is_connected", lambda db: True)
    monkeypatch.setattr(pipelines.gmail, "fetch_recent", lambda db, since_days=2: list(messages))


def test_only_newest_message_in_thread_is_classified(db, monkeypatch):
    calls = []

    def classify(sender, subject, body, tracked):
        calls.append(subject)
        return {"category": "interview_invite", "summary": subject, "urgency": 2}

    _wire_gmail(monkeypatch, [_msg("m1", "t1", 60, "interview at Stripe"),
                              _msg("m2", "t1", 5, "interview rescheduled at Stripe")])
    monkeypatch.setattr(pipelines.email_classifier, "classify", classify)

    run = pipelines.email_scan(db)
    assert run.ok, run.summary
    assert calls == ["interview rescheduled at Stripe"]  # older message never hits the LLM
    older = db.scalar(select(Email).where(Email.gmail_id == "m1"))
    assert older.classification["category"] == "superseded_in_thread"
    assert db.scalar(select(Alert.title).where(Alert.dismissed.is_(False))).endswith("rescheduled at Stripe")


def test_newer_thread_message_supersedes_older_alert(db, monkeypatch):
    def classify(sender, subject, body, tracked):
        return {"category": "interview_invite", "summary": subject, "urgency": 2}

    monkeypatch.setattr(pipelines.email_classifier, "classify", classify)
    _wire_gmail(monkeypatch, [_msg("m1", "t1", 60, "interview Tue")])
    pipelines.email_scan(db)
    _wire_gmail(monkeypatch, [_msg("m1", "t1", 60, "interview Tue"), _msg("m2", "t1", 5, "moved to Thu")])
    pipelines.email_scan(db)

    alerts = list(db.scalars(select(Alert)))
    live = [a for a in alerts if not a.dismissed]
    assert len(alerts) == 2 and len(live) == 1
    assert live[0].title.endswith("moved to Thu")


def test_garbage_application_id_does_not_crash_scan(db, monkeypatch):
    def classify(sender, subject, body, tracked):
        return {"category": "online_assessment", "application_id": "not-a-number", "summary": subject, "urgency": 2}

    _wire_gmail(monkeypatch, [_msg("m1", "t1", 5, "assessment invite")])
    monkeypatch.setattr(pipelines.email_classifier, "classify", classify)
    run = pipelines.email_scan(db)
    assert run.ok, run.summary
    alert = db.scalar(select(Alert))
    assert alert is not None and alert.application_id is None


class _FakeSource(JobSource):
    name = "fake"

    def search(self, queries, locations):
        return [RawJob(external_id="fake:1", source="fake", company="Acme", role="SWE Intern", url="http://x")]


def test_job_scan_commits_jobs_even_when_scoring_fails(db, monkeypatch):
    from app.models import Profile
    db.add(Profile(id=1, target_roles=["SWE Intern"], llm_summary="intern"))
    db.commit()
    monkeypatch.setattr(pipelines, "active_sources", lambda: [_FakeSource()])

    def boom(profile, applied, jobs, verdicts=None):
        raise RuntimeError("LLM down")

    monkeypatch.setattr(pipelines.matcher, "score_batch", boom)
    run = pipelines.job_scan(db)
    assert not run.ok
    job = db.scalar(select(DiscoveredJob))
    assert job is not None and job.match_score is None  # find persisted, score missing

    # Next run rescores the leftover instead of dropping it forever.
    monkeypatch.setattr(pipelines.matcher, "score_batch",
                        lambda profile, applied, jobs, verdicts=None: {j.id: {"score": 90.0, "reason": "fits"} for j in jobs})
    run = pipelines.job_scan(db)
    assert run.ok, run.summary
    db.refresh(job)
    assert job.match_score == 90.0
    assert db.scalar(select(Alert).where(Alert.kind == "discovery")) is not None


def test_email_scan_skips_when_disconnected(db, monkeypatch):
    monkeypatch.setattr(pipelines.gmail, "is_connected", lambda db: False)
    run = pipelines.email_scan(db)
    assert run.ok and "skipped" in run.summary


def test_deadline_check_alerts_once_per_day(db):
    db.add(Application(company="Acme", role="SWE", status=ApplicationStatus.applied,
                       next_action="OA", next_action_at=datetime.utcnow() + timedelta(days=1)))
    db.commit()
    pipelines.deadline_check(db)
    pipelines.deadline_check(db)
    alerts = list(db.scalars(select(Alert).where(Alert.kind == "deadline")))
    assert len(alerts) == 1
