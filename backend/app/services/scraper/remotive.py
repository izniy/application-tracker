"""Remotive public API — remote roles, no key needed. Good default so Discover works on day one."""
from datetime import datetime

import httpx

from .base import JobSource, RawJob


class RemotiveSource(JobSource):
    name = "remotive"

    def search(self, queries, locations):
        out: list[RawJob] = []
        with httpx.Client(timeout=20) as client:
            for q in queries[:4]:
                r = client.get("https://remotive.com/api/remote-jobs", params={"search": q, "limit": 30})
                if r.status_code != 200:
                    continue
                for j in r.json().get("jobs", []):
                    out.append(RawJob(
                        external_id=f"remotive:{j['id']}",
                        source=self.name,
                        company=j.get("company_name", ""),
                        role=j.get("title", ""),
                        url=j.get("url", ""),
                        location=j.get("candidate_required_location") or "Remote",
                        description=j.get("description"),
                        posted_at=_parse(j.get("publication_date")),
                    ))
        return out


def _parse(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None
