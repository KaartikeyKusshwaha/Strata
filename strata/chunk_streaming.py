"""LRU chunk cache manager for edit-time chunk paging and working set streaming.

No bpy imports required.
"""
from __future__ import annotations

from collections import OrderedDict
from typing import Dict, List, Set, Tuple

ChunkKey3D = Tuple[int, int, int]


class ChunkLRUCache:
    def __init__(
        self,
        max_loaded_chunks: int = 27,
        radius_x: int = 1,
        radius_y: int = 1,
        radius_z: int = 1,
    ):
        self.max_loaded_chunks = max_loaded_chunks
        self.radius_x = radius_x
        self.radius_y = radius_y
        self.radius_z = radius_z

        self._cache: OrderedDict[ChunkKey3D, bool] = OrderedDict()
        self._pinned: Set[ChunkKey3D] = set()

    def touch(self, chunk_key: ChunkKey3D):
        """Marks a chunk as recently accessed."""
        if chunk_key in self._cache:
            self._cache.move_to_end(chunk_key)
        else:
            self._cache[chunk_key] = True

    def pin(self, chunk_key: ChunkKey3D):
        """Pins a chunk so it is excluded from LRU eviction."""
        self._pinned.add(chunk_key)
        self.touch(chunk_key)

    def unpin(self, chunk_key: ChunkKey3D):
        """Unpins a chunk."""
        self._pinned.discard(chunk_key)

    def is_pinned(self, chunk_key: ChunkKey3D) -> bool:
        return chunk_key in self._pinned

    def get_working_set_chunks(self, center_key: ChunkKey3D) -> List[ChunkKey3D]:
        """Calculates 3D chunk keys within radius around center (cx, cy, cz)."""
        cx, cy, cz = center_key
        chunks = []
        for dx in range(-self.radius_x, self.radius_x + 1):
            for dy in range(-self.radius_y, self.radius_y + 1):
                for dz in range(-self.radius_z, self.radius_z + 1):
                    chunks.append((cx + dx, cy + dy, cz + dz))
        return chunks

    def update_working_set(
        self, center_key: ChunkKey3D, available_manifest_chunks: List[ChunkKey3D]
    ) -> Tuple[List[ChunkKey3D], List[ChunkKey3D]]:
        """Updates the active working set around center_key.

        Returns (to_load, to_unload).
        """
        requested = set(self.get_working_set_chunks(center_key))
        valid_requested = [ck for ck in requested if ck in available_manifest_chunks]

        to_load = [ck for ck in valid_requested if ck not in self._cache]

        # Touch all requested valid chunks
        for ck in valid_requested:
            self.touch(ck)

        # Calculate LRU eviction if cache size exceeds max_loaded_chunks
        to_unload = []
        while len(self._cache) > self.max_loaded_chunks:
            # Find oldest unpinned chunk outside active working set
            evicted_key = None
            for key in self._cache:
                if key not in self._pinned and key not in requested:
                    evicted_key = key
                    break

            if evicted_key is None:
                # Fallback to oldest unpinned chunk
                for key in self._cache:
                    if key not in self._pinned:
                        evicted_key = key
                        break

            if evicted_key is not None:
                del self._cache[evicted_key]
                to_unload.append(evicted_key)
            else:
                # All chunks are pinned
                break

        return to_load, to_unload

    def get_loaded_chunks(self) -> List[ChunkKey3D]:
        return list(self._cache.keys())

    def get_pinned_chunks(self) -> List[ChunkKey3D]:
        return list(self._pinned)

    def unload(self, chunk_key: ChunkKey3D) -> bool:
        if chunk_key in self._cache and chunk_key not in self._pinned:
            del self._cache[chunk_key]
            return True
        return False

    def unload_all_unpinned(self) -> List[ChunkKey3D]:
        unloaded = []
        keys = list(self._cache.keys())
        for key in keys:
            if key not in self._pinned:
                del self._cache[key]
                unloaded.append(key)
        return unloaded
