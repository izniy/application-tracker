"""Adzuna — keyed API with country endpoints (sg, gb, us, ...). Free tier is generous."""
from datetime import datetime

import httpx

from ...config import settings
from .base import JobSource, RawJob


class AdzunaSource(JobSource):
    name = "adzuna"

    def enabled(self):
        return bool(settings.adzuna_app_id and settings.adzuna_app_key)

    def search(self, queries, locations):
        out: list[RawJob] = []
        base = f"https://api.adzuna.com/v1/api/jobs/{settings.adzuna_country}/search/1"
        with httpx.Client(timeout=20) as client:
            for q in queries[:4]:
                r = client.get(base, params={
                    "app_id": settings.adzuna_app_id,
                    "app_key": settings.adzuna_app_key,
                    "what": q,
                    "results_per_page": 25,
                    "max_days_old": 3,
                    "content-type": "application/json",
                })
                if r.status_code != 200:
                    continue
                for j in r.json().get("results", []):
                    out.append(RawJob(
                        external_id=f"adzuna:{j['id']}",
                        source=self.name,
                        company=(j.get("company") or {}).get("display_name", ""),
                        role=j.get("title", ""),
                        url=j.get("redirect_url", ""),
                        location=(j.get("location") or {}).get("display_name"),
                        description=j.get("description"),
                        posted_at=_parse(j.get("created")),
                    ))
        return out


def _parse(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None
