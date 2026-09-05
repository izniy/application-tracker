from .adzuna import AdzunaSource
from .base import JobSource
from .remotive import RemotiveSource

# Order matters only for logging. TODO: add LinkedIn/Greenhouse/Lever adapters here.
SOURCES: list[JobSource] = [AdzunaSource(), RemotiveSource()]


def active_sources() -> list[JobSource]:
    return [s for s in SOURCES if s.enabled()]
