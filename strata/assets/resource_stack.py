"""Resource pack manager for tracking packed image bytes and texture resources."""
from __future__ import annotations

from typing import Dict, Optional, List


class ResourcePackManager:
    def __init__(self, texture_sources: Optional[List[Any]] = None):
        self.texture_sources = texture_sources or []
        self._image_cache: Dict[str, bytes] = {}

    def add_image(self, texture_ref: str, image_bytes: bytes):
        self._image_cache[texture_ref] = image_bytes

    def get_image(self, texture_ref: str) -> Optional[bytes]:
        return self._image_cache.get(texture_ref)

    def list_images(self) -> Dict[str, bytes]:
        return self._image_cache.copy()
