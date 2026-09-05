"""Turn a raw email into a structured classification the alert engine can act on."""
from ..models import Application
from . import llm

SYSTEM = """You classify emails in a job-seeker's inbox. Be conservative: only claim a status
change when the email clearly states it. Recruiter spam and newsletters are 'not_job_related'."""

CATEGORIES = [
    "not_job_related",
    "application_received",   # confirmation of submission
    "online_assessment",      # OA / coding test link
    "interview_invite",       # scheduling or invite
    "interview_followup",     # thank-you, next steps, additional info requested
    "offer",
    "rejection",
    "recruiter_outreach",     # new company reaching out
    "other_job_related",
]

STATUS_FOR_CATEGORY = {
    "application_received": "applied",
    "online_assessment": "online_assessment",
    "interview_invite": "interviewing",
    "interview_followup": "interviewing",
    "offer": "offer",
    "rejection": "rejected",
}


def classify(sender: str, subject: str, body: str, tracked: list[Application]) -> dict:
    companies = [
        {"id": a.id, "company": a.company, "role": a.role, "status": a.status.value}
        for a in tracked
    ]
    user = f"""Tracked applications (match the email to one of these ids if it belongs to it):
{companies}

Email
From: {sender}
Subject: {subject}
Body:
{body[:6000]}

Return JSON with keys:
- category: one of {CATEGORIES}
- application_id: matching id from the list, or null
- company: company name as written in the email, or null
- role: role mentioned, or null
- summary: one sentence a busy student can act on
- action_required: true/false — does the user need to do something?
- action: short imperative if action_required (e.g. "Complete HackerRank OA by 12 Sep"), else null
- deadline: ISO date if one is stated, else null
- urgency: 1 (fyi), 2 (respond this week), 3 (respond today)"""
    result = llm.complete_json(SYSTEM, user, max_tokens=500)
    result.setdefault("category", "not_job_related")
    result["suggested_status"] = STATUS_FOR_CATEGORY.get(result["category"])
    return result
