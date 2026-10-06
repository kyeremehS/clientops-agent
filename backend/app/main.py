"""Entrypoint. Wiring only — no business logic."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.leads import router as leads_router
from app.config import settings
from app.db.base import Base, get_engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Slice 1: create tables on startup. Migrations (Alembic) come later.
    Base.metadata.create_all(get_engine(settings.database_url))
    yield


# Slice 1 dev: the queue UI may land on any localhost port (3000, 3001, ...
# when the default is busy), so match by regex instead of listing ports.
DEV_ORIGIN_REGEX = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"


app = FastAPI(title="clientops-agent", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=DEV_ORIGIN_REGEX,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(leads_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
