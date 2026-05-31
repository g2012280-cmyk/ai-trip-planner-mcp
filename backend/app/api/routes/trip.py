import logging

from fastapi import APIRouter, HTTPException

from app.agents.trip_planner_agent import TripPlannerAgent
from app.config import get_settings
from app.models.schemas import TripPlan, TripPlanRequest
from app.services.unsplash_service import UnsplashService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trip", tags=["trip"])

# 单例初始化
_trip_planner: TripPlannerAgent | None = None
_unsplash: UnsplashService | None = None


def get_trip_planner() -> TripPlannerAgent:
    global _trip_planner
    if _trip_planner is None:
        _trip_planner = TripPlannerAgent()
    return _trip_planner


def get_unsplash() -> UnsplashService:
    global _unsplash
    if _unsplash is None:
        settings = get_settings()
        _unsplash = UnsplashService(settings.unsplash_access_key, settings.serpapi_api_key)
    return _unsplash


@router.post("/plan", response_model=TripPlan)
async def create_trip_plan(request: TripPlanRequest) -> TripPlan:
    """生成旅行计划"""
    print(f"[TRIP] 收到请求: {request.city}", flush=True)
    logger.info(f"收到规划请求: {request.city}")
    try:
        trip_plan = await get_trip_planner().plan_trip(request)

        # 为景点补充图片（Unsplash 可选，跨景点去重）
        unsplash = get_unsplash()
        used_urls: set = set()

        # Count attractions needing images
        total = sum(1 for day in trip_plan.days for a in day.attractions if not a.image_url)
        # Pre-fetch city pool so fallbacks are varied and non-repeating
        city_pool = unsplash.build_city_pool(trip_plan.city, need=total * 2)
        city_pool_iter = iter(url for url in city_pool if url not in used_urls)

        for day in trip_plan.days:
            for attraction in day.attractions:
                if not attraction.image_url:
                    url = unsplash.get_photo_url(attraction.name, trip_plan.city, used_urls)
                    if url is None:
                        # Draw from pre-fetched city pool
                        url = next((u for u in city_pool if u not in used_urls), None)
                        if url:
                            used_urls.add(url)
                    attraction.image_url = url

        return trip_plan
    except Exception as e:
        logger.error(f"生成计划失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成计划失败: {str(e)}")


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}
