"""Turn a raw email into a structured classification the alert engine can act on."""
from ..models import Application
from . import llm

SYSTEM = """You classify emails in a job-seeker's inbox. Every category other than
'not_job_related' raises an alert, and a false alert costs more trust than a missed one:
when unsure whether an email is about the user's OWN applications or job search, choose 'not_job_related'.

Always 'not_job_related', no matter how much hiring language they contain:
- job-board digests and saved-search alerts (LinkedIn "new jobs for you", Indeed, Glassdoor)
- career newsletters, career-fair or campus-recruiting announcements, bootcamp/course promotions
- company product updates or marketing, even with a "we're hiring" footer
- automated notifications from tools and shops (GitHub, order/shipping confirmations, receipts) —
  including from companies the user has applied to

Category rules:
- application_received: an ATS or company auto-confirmation that a submitted application was received
  (Greenhouse, Lever, Workday, Ashby, SmartRecruiters, ...).
- online_assessment: an invitation or reminder to take a coding test / OA (HackerRank, Codility,
  CodeSignal, HireVue, ...) as part of the user's application. The tracked list is not exhaustive —
  the user applies to more companies than it holds. An email that references the user's own
  application ("as part of your application", "you have been invited to complete") is about their
  job search even when the company is untracked: classify it normally and set application_id to null.
- interview_invite: scheduling, proposing times for, or confirming an interview — including calendar invitations.
- interview_followup: post-interview thanks/next-steps, or the company requesting documents or
  information to continue the user's application.
- offer / rejection: only when the outcome is clearly stated. Polite closures like "we'll keep your
  resume on file" after a decision are rejections.
- recruiter_outreach: a person (recruiter, hiring manager, agency) writing to the user about a
  specific opportunity they have not applied to. Mass-mailed job lists are not outreach.
- other_job_related: clearly about the user's own job search but none of the above — including
  personal mail about it, e.g. a friend confirming they submitted a referral for the user.

Field rules:
- application_id: only when the sender or body clearly identifies exactly one tracked application's
  company (and the email concerns that application). An order receipt from a tracked company is NOT
  about the application. Never guess between two; use null.
- suggested status changes are proposals the user confirms — be conservative.
- deadline: only when an explicit date/deadline is stated; convert to ISO format. Use the stated year;
  the current year if none is stated.
- urgency: 3 = act today or a hard deadline within ~48h; 2 = respond this week; 1 = FYI, no action."""

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

Return JSON with keys, in this order:
- reasoning: one sentence weighing whether this concerns the user's OWN job search, written before you commit to a category
- category: one of {CATEGORIES}
- application_id: matching id from the list, or null
- company: company name as written in the email, or null
- role: role mentioned, or null
- summary: one sentence a busy student can act on
- action_required: true/false — does the user need to do something?
- action: short imperative if action_required (e.g. "Complete HackerRank OA by 12 Sep"), else null
- deadline: ISO date if one is stated, else null
- urgency: 1 (fyi), 2 (respond this week), 3 (respond today)"""
    result = llm.complete_json(SYSTEM, user, max_tokens=600)
    result.setdefault("category", "not_job_related")
    result["suggested_status"] = STATUS_FOR_CATEGORY.get(result["category"])
    return result
