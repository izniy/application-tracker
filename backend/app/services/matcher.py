"""Score discovered jobs against the profile and the roles already applied to."""
from ..models import Application, DiscoveredJob, Profile
from . import llm

SYSTEM = """You are a job-fit scorer for a specific candidate. Score realistically: a 90 means
they should apply today; below 50 means not worth their time. Penalise seniority mismatch and
locations outside their target list heavily. If past verdicts are given, treat them as taste:
score jobs like ones they saved higher and jobs like ones they dismissed lower."""


def score_batch(profile: Profile, applied: list[Application], jobs: list[DiscoveredJob],
                verdicts: list[DiscoveredJob] | None = None) -> dict[int, dict]:
    """Returns {job.id: {score, reason}}. Batched to keep LLM calls low."""
    if not jobs:
        return {}
    applied_summary = [f"{a.role} @ {a.company} ({a.location or 'n/a'})" for a in applied[:25]]
    verdict_summary = [f"{v.verdict}: {v.role} @ {v.company} ({v.location or 'n/a'}, scored {v.match_score or '?'})"
                       for v in verdicts or []]
    listing = [
        {
            "id": j.id,
            "company": j.company,
            "role": j.role,
            "location": j.location,
            "description": (j.description or "")[:1200],
        }
        for j in jobs
    ]
    user = f"""Candidate profile:
{profile.llm_summary or profile.headline or 'No profile yet.'}

Target roles: {profile.target_roles}
Target locations: {profile.target_locations}
Seniority: {profile.seniority} | Availability: {profile.availability}

Roles they have already applied to (signal of what they want):
{applied_summary}

Their verdicts on jobs Orbit found earlier (saved = interested, dismissed = not interested):
{verdict_summary or 'none yet'}

Jobs to score:
{listing}

Return JSON: {{"scores": [{{"id": <job id>, "score": 0-100, "reason": "<= 25 words"}}]}}"""
    data = llm.complete_json(SYSTEM, user, max_tokens=2000)
    return {int(s["id"]): {"score": float(s["score"]), "reason": s.get("reason", "")}
            for s in data.get("scores", []) if "id" in s and "score" in s}
