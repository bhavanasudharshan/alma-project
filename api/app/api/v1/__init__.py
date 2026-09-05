"""Version 1 of the HTTP API."""

from fastapi import APIRouter

from app.api.v1 import auth, health, leads

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(leads.router)
