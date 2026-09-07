import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # noqa: F401  (registers tables)
from .config import settings
from .database import Base, engine
from .routers import alerts, applications, email, jobs, profile, system
from .scheduler import start as start_scheduler
from .services import llm

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    start_scheduler()
    yield


app = FastAPI(title="Orbit", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_methods=["*"], allow_headers=["*"])

for r in (applications, alerts, jobs, profile, email, system):
    app.include_router(r.router)


@app.get("/api/health")
def health():
    return {"ok": True, "llm_configured": llm.is_configured()}
