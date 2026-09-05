"""Evaluate the email classifier against fixture emails with the real model.

These tests call the live LLM, so they need ANTHROPIC_API_KEY (in the environment
or backend/.env) and are skipped without it. They are an eval, not a unit test:
run them after changing the prompt in email_classifier.py.

The bar, in order of importance:
1. No false alerts — every newsletter/digest/receipt fixture must classify as
   not_job_related. A wrong alert costs more trust than a missed one.
2. Real signals get the right category, and link only to the right application.
"""
import json
from pathlib import Path

import pytest

from app.config import settings
from app.models import Application, ApplicationStatus
from app.services import email_classifier

FIXTURES = json.loads((Path(__file__).parent / "fixtures" / "emails.json").read_text())

TRACKED = [
    Application(id=t["id"], company=t["company"], role=t["role"], status=ApplicationStatus(t["status"]))
    for t in FIXTURES["tracked"]
]

needs_llm = pytest.mark.skipif(not settings.anthropic_api_key, reason="ANTHROPIC_API_KEY not set")


def _classify(email: dict) -> dict:
    return email_classifier.classify(email["sender"], email["subject"], email["body"], TRACKED)


@needs_llm
@pytest.mark.parametrize("email", FIXTURES["emails"], ids=[e["id"] for e in FIXTURES["emails"]])
def test_classification(email: dict):
    expect = email["expect"]
    got = _classify(email)

    assert got.get("category") in expect["category"], (
        f"category {got.get('category')!r} not in {expect['category']} — full output: {got}"
    )

    got_app = got.get("application_id")
    got_app = int(got_app) if got_app is not None else None
    assert got_app == expect["application_id"], (
        f"linked to application {got_app!r}, expected {expect['application_id']!r} — full output: {got}"
    )

    if "urgency" in expect and got.get("category") != "not_job_related":
        assert int(got.get("urgency") or 0) in expect["urgency"], (
            f"urgency {got.get('urgency')!r} not in {expect['urgency']} — full output: {got}"
        )

    if "deadline_contains" in expect:
        assert expect["deadline_contains"] in str(got.get("deadline")), (
            f"deadline {got.get('deadline')!r} should contain {expect['deadline_contains']!r}"
        )
