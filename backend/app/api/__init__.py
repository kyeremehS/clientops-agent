"""API layer. Routers live here; Pydantic schemas are the contract."""

from app.api.leads import router as leads_router

__all__ = ["leads_router"]
