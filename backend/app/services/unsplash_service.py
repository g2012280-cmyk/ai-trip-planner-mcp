import logging
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class UnsplashService:
    def __init__(self, access_key: str):
        self.access_key = access_key
        self._enabled = bool(access_key and "your_" not in access_key)

    def search_photos(self, query: str, per_page: int = 5) -> List[Dict]:
        if not self._enabled:
            return []
        try:
            response = requests.get(
                "https://api.unsplash.com/search/photos",
                params={"query": query, "per_page": per_page, "client_id": self.access_key},
                timeout=10,
            )
            response.raise_for_status()
            return [
                {
                    "url": r["urls"]["regular"],
                    "description": r.get("description", ""),
                    "photographer": r["user"]["name"],
                }
                for r in response.json().get("results", [])
            ]
        except Exception as e:
            logger.warning(f"Unsplash search failed: {e}")
            return []

    def get_photo_url(self, query: str) -> Optional[str]:
        photos = self.search_photos(query, per_page=1)
        return photos[0]["url"] if photos else None
