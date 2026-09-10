"""Condense resume + form fields into a short profile the matcher and classifier can reuse."""
from ..models import Profile
from . import llm

SYSTEM = """You are a careful career assistant. Produce a compact, factual candidate profile
for use in job matching. Do not invent skills or experience that are not present."""


def build_summary(profile: Profile) -> str:
    fields = {
        "name": profile.name,
        "headline": profile.headline,
        "location": profile.location,
        "target_roles": profile.target_roles,
        "target_levels": profile.target_levels,
        "target_locations": profile.target_locations,
        "tech_stack": profile.skills,
        "seniority": profile.seniority,
        "availability": profile.availability,
        "preferences": profile.preferences,
    }
    user = f"""Structured fields:
{fields}

Resume text:
{(profile.resume_text or '')[:12000]}

Write a 150-250 word profile covering: seniority/availability, strongest technical areas with evidence,
the kinds of roles and companies that fit, and explicit dealbreakers. Plain prose, no headings."""
    return llm.complete(SYSTEM, user, max_tokens=600).strip()
