"""Template inventory manager for caching and tracking resolved prototype assets."""
from __future__ import annotations

from typing import Dict, Any, Optional


class TemplateInventory:
    def __init__(self):
        self._inventory: Dict[str, Dict[str, Any]] = {}

    def register(self, block_id: str, template_data: Dict[str, Any]):
        self._inventory[block_id] = template_data

    def get(self, block_id: str) -> Optional[Dict[str, Any]]:
        return self._inventory.get(block_id)

    def contains(self, block_id: str) -> bool:
        return block_id in self._inventory

    def list_all(self) -> Dict[str, Dict[str, Any]]:
        return self._inventory.copy()
