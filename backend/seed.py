"""Populate a fresh DB with sample data so the UI has something to show. Run: python seed.py"""
from datetime import datetime, timedelta

from app.database import Base, SessionLocal, engine
from app.models import Alert, AlertKind, Application, ApplicationStatus, DiscoveredJob, Profile, StatusEvent

Base.metadata.create_all(engine)
db = SessionLocal()
now = datetime.utcnow()

apps = [
    Application(company="Stripe", role="Software Engineer Intern", location="Singapore", status=ApplicationStatus.interviewing, applied_at=now - timedelta(days=12), next_action="Prepare for system design round", next_action_at=now + timedelta(days=2), company_domains=["stripe.com"]),
    Application(company="Grab", role="Data Platform Intern", location="Singapore", status=ApplicationStatus.online_assessment, applied_at=now - timedelta(days=5), next_action="Complete HackerRank OA", next_action_at=now + timedelta(days=1), company_domains=["grab.com"]),
    Application(company="Shopee", role="Backend Engineer Intern", location="Singapore", status=ApplicationStatus.applied, applied_at=now - timedelta(days=3)),
    Application(company="Anthropic", role="Software Engineer, Infrastructure (Intern)", location="Remote", status=ApplicationStatus.applied, applied_at=now - timedelta(days=1)),
    Application(company="Bytedance", role="ML Infra Intern", location="Singapore", status=ApplicationStatus.rejected, applied_at=now - timedelta(days=30)),
    Application(company="Databricks", role="Software Engineering Intern", location="Singapore", status=ApplicationStatus.saved),
]
db.add_all(apps)
db.flush()
for a in apps:
    db.add(StatusEvent(application_id=a.id, to_status=a.status.value, source="manual", created_at=a.applied_at or now))

db.add_all([
    Alert(kind=AlertKind.assessment, title="Grab: Complete HackerRank OA by tomorrow", body="Link expires in 24h", application_id=apps[1].id, urgency=3),
    Alert(kind=AlertKind.interview, title="Stripe: Recruiter proposed Thu 10:00 for round 2", body="Reply to confirm the slot", application_id=apps[0].id, urgency=2),
    Alert(kind=AlertKind.new_company, title="Coinbase: Recruiter reached out about a platform intern role", body="Not in your pipeline yet", urgency=1),
    Alert(kind=AlertKind.status_update, title="Shopee: Application received", application_id=apps[2].id, urgency=1, read=True),
])

db.add_all([
    DiscoveredJob(external_id="seed:1", source="adzuna", company="GovTech", role="Software Engineer Intern (Data Platform)", location="Singapore", url="https://example.com/1", match_score=88, match_reason="Data infra focus, Singapore, intern-level, matches Spark/Python skills."),
    DiscoveredJob(external_id="seed:2", source="remotive", company="Vercel", role="Infrastructure Engineering Intern", location="Remote", url="https://example.com/2", match_score=76, match_reason="Strong infra fit; remote may need visa check."),
    DiscoveredJob(external_id="seed:3", source="adzuna", company="Sea", role="Senior Data Engineer", location="Singapore", url="https://example.com/3", match_score=31, match_reason="Seniority mismatch."),
])

db.merge(Profile(id=1, name="Yin Zi", headline="Final-year CS student, data infra & applied AI", location="Singapore",
                 target_roles=["Software Engineer Intern", "Data Infrastructure Intern", "ML Engineer Intern"],
                 target_locations=["Singapore", "Remote"], skills=["Python", "TypeScript", "Spark", "Postgres", "LLM evals"],
                 seniority="intern", availability="Internship Feb–May 2027; full-time from Jun 2027"))
db.commit()
print("seeded")
