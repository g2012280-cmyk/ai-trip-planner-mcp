from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""

    # DeepSeek API
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # 高德地图 API
    amap_api_key: str = ""

    # Unsplash API（可选）
    unsplash_access_key: str = ""

    # SerpAPI（图片搜索）
    serpapi_api_key: str = ""

    # 应用配置
    app_name: str = "智能旅行助手"
    debug: bool = False

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    """获取配置（单例）"""
    return Settings()
