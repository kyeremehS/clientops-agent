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


# Slice 1 dev origins. Browsers block cross-origin UI → API calls without these.
DEV_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]


app = FastAPI(title="clientops-agent", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=DEV_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(leads_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
