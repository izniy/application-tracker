# Orbit

Mission control for a job search. Tracks applications, reads your inbox every morning and turns it into
alerts, and finds new roles that match your profile — so a busy student or worker only has to decide, not dig.

## Run locally

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate      # or: conda create -n orbit python=3.12
pip install -r requirements.txt
cp .env.example .env                                  # add ANTHROPIC_API_KEY at minimum
python seed.py                                        # optional sample data
uvicorn app.main:app --reload

# frontend (new terminal)
cd frontend
npm install
npm run dev                                           # http://localhost:5173 (proxies /api to :8000)
```

## Gmail connection

Create an OAuth client in Google Cloud Console (type **Web application**, redirect URI
`http://localhost:8000/api/email/oauth/callback`, scope `gmail.readonly`, and add yourself as a
test user while the consent screen is in testing). Put `GOOGLE_CLIENT_ID` and
`GOOGLE_CLIENT_SECRET` in `backend/.env`, restart the backend, then click **Connect Gmail** in
Settings. If Google ever revokes the token, Orbit clears it and raises a signal asking to reconnect.

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest                    # classifier eval needs ANTHROPIC_API_KEY; skipped otherwise
ruff check app/ seed.py
```

The classifier tests in `tests/test_classifier.py` run fixture emails (ATS confirmations, OA
invites, recruiter mail, digests) through the live model. The hard rule: newsletter/digest/receipt
fixtures must never classify as job mail — false alerts are worse than missed ones.

## What is wired up

| Piece | Where | Status |
|---|---|---|
| Applications CRUD, status history, kanban drag/drop | `routers/applications.py`, `pages/Board.tsx` | working |
| Daily Gmail scan → LLM classification → alerts + suggested status | `services/gmail.py`, `email_classifier.py`, `pipelines.email_scan` | working, needs Google OAuth creds |
| Daily job discovery → LLM match scoring → Discover page | `services/scraper/*`, `matcher.py`, `pipelines.job_scan` | working (Remotive keyless; Adzuna keyed) |
| Deadline alerts, auto-"no response" after 30 days | `pipelines.deadline_check` | working |
| Profile + resume upload + LLM profile summary | `routers/profile.py`, `pages/Profile.tsx` | working |
| Scheduler (07:00 jobs, 08:00 email, 08:30 deadlines) | `scheduler.py` | working |
