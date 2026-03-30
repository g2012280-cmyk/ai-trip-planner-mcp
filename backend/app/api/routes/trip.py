import logging

from fastapi import APIRouter, HTTPException

from app.agents.trip_planner_agent import TripPlannerAgent
from app.config import get_settings
from app.models.schemas import TripPlan, TripPlanRequest
from app.services.unsplash_service import UnsplashService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trip", tags=["trip"])

_planner: TripPlannerAgent | None = None
_unsplash: UnsplashService | None = None


def get_planner() -> TripPlannerAgent:
    global _planner
    if _planner is None:
        _planner = TripPlannerAgent()
    return _planner


def get_unsplash() -> UnsplashService:
    global _unsplash
    if _unsplash is None:
        _unsplash = UnsplashService(get_settings().unsplash_access_key)
    return _unsplash


@router.post("/plan", response_model=TripPlan)
async def create_trip_plan(request: TripPlanRequest) -> TripPlan:
    try:
        trip = get_planner().plan_trip(request)

        unsplash = get_unsplash()
        for day in trip.days:
            for attraction in day.attractions:
                if not attraction.image_url:
                    attraction.image_url = unsplash.get_photo_url(
                        f"{attraction.name} {trip.city}"
                    )
        return trip
    except Exception as e:
        logger.error(f"Failed to generate trip plan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    return {"status": "ok"}
