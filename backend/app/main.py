"""Entrypoint. Wiring only — no business logic."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.leads import router as leads_router
from app.config import settings
from app.db.base import Base, get_engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Slice 1: create tables on startup. Migrations (Alembic) come later.
    Base.metadata.create_all(get_engine(settings.database_url))
    yield


app = FastAPI(title="clientops-agent", lifespan=lifespan)
app.include_router(leads_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
