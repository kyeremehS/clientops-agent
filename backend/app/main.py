"""Entrypoint. Wiring only — no business logic."""

from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.actions import router as actions_router
from app.api.leads import router as leads_router
from app.api.runs import router as runs_router


def _alembic_config() -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(Path(__file__).resolve().parent.parent / "alembic"))
    return cfg


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Migrations own the schema. Tests exercise this path too: TestClient
    # startup runs these same migrations against the test database.
    command.upgrade(_alembic_config(), "head")
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
app.include_router(actions_router)
app.include_router(runs_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
