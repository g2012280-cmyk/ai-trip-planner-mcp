import logging
from typing import List, Optional, Set

import requests

logger = logging.getLogger(__name__)

# 中文城市名 → 英文，供 Unsplash 搜索使用
CITY_EN = {
    "北京": "Beijing", "上海": "Shanghai", "广州": "Guangzhou", "深圳": "Shenzhen",
    "杭州": "Hangzhou", "成都": "Chengdu", "西安": "Xian", "重庆": "Chongqing",
    "南京": "Nanjing", "苏州": "Suzhou", "厦门": "Xiamen", "青岛": "Qingdao",
    "武汉": "Wuhan", "长沙": "Changsha", "昆明": "Kunming", "桂林": "Guilin",
    "三亚": "Sanya", "丽江": "Lijiang", "张家界": "Zhangjiajie", "黄山": "Huangshan",
    "乌鲁木齐": "Urumqi", "拉萨": "Lhasa", "哈尔滨": "Harbin", "天津": "Tianjin",
}

_UNSPLASH_SEARCH = "https://api.unsplash.com/search/photos"


class UnsplashService:
    """使用 Unsplash API 为景点搜索高质量图片。"""

    def __init__(self, access_key: str, serpapi_key: str = ""):
        # serpapi_key 保留参数兼容性，不再使用
        self.access_key = access_key
        self._enabled = bool(access_key)

    def _search(self, query: str, count: int = 10) -> List[str]:
        """向 Unsplash 搜索图片，返回 regular 尺寸 URL 列表。"""
        if not self._enabled:
            logger.warning("Unsplash 未启用：access_key 为空")
            return []
        try:
            resp = requests.get(
                _UNSPLASH_SEARCH,
                params={
                    "query": query,
                    "per_page": count,
                    "orientation": "landscape",
                },
                headers={"Authorization": f"Client-ID {self.access_key}"},
                timeout=10,
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            urls = [r["urls"]["regular"] for r in results if r.get("urls", {}).get("regular")]
            logger.info(f"Unsplash 搜索 '{query}': 返回 {len(urls)} 张")
            return urls
        except Exception as e:
            logger.warning(f"Unsplash 搜索失败 ({query}): {e}")
            return []

    def build_city_pool(self, city_zh: str, need: int) -> List[str]:
        """预取城市通用图片作为兜底池。优先用英文名搜索，质量更高。"""
        city_en = CITY_EN.get(city_zh, city_zh)
        pool: List[str] = []
        seen: Set[str] = set()

        for query in [f"{city_en} travel", f"{city_en} landmark", f"{city_en} scenery"]:
            if len(pool) >= need:
                break
            for url in self._search(query, count=10):
                if url not in seen:
                    seen.add(url)
                    pool.append(url)
        return pool

    def get_photo_url(self, attraction_name: str, city_zh: str, used: Set[str]) -> Optional[str]:
        """搜索景点专属图片，优先用英文 + 中文双重查询。"""
        if not self._enabled:
            return None

        city_en = CITY_EN.get(city_zh, city_zh)

        # 先用景点名（中文）+ 城市英文搜索
        for url in self._search(f"{attraction_name} {city_en}", count=10):
            if url not in used:
                used.add(url)
                return url

        # 降级：只用城市英文搜索
        for url in self._search(f"{city_en} attraction", count=10):
            if url not in used:
                used.add(url)
                return url

        return None
