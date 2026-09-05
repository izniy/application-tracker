"""Every job source implements `search(queries, locations) -> list[RawJob]`.
Add a new source by subclassing JobSource and registering it in registry.py."""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RawJob:
    external_id: str   # must be globally unique: prefix with source name
    source: str
    company: str
    role: str
    url: str
    location: str | None = None
    description: str | None = None
    posted_at: datetime | None = None


class JobSource:
    name = "base"

    def enabled(self) -> bool:
        return True

    def search(self, queries: list[str], locations: list[str]) -> list[RawJob]:
        raise NotImplementedError
