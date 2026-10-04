"""Scaffold entrypoint. Health stub only — no business logic yet."""

from fastapi import FastAPI

app = FastAPI(title="clientops-agent")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
