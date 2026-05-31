import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import trip
from app.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log", encoding="utf-8"),
    ]
)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="基于多 Agent 的智能旅行规划 API",
    version="1.0.0",
    debug=settings.debug,
)

# 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(trip.router, prefix="/api")


@app.get("/")
async def root():
    return {"message": f"欢迎使用{settings.app_name}", "docs": "/docs"}
