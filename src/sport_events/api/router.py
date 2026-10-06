from fastapi import APIRouter

from sport_events.api.routes.football import router as football_router
from sport_events.api.routes.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(football_router)
