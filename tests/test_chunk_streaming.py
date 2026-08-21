"""Unit tests for LRU chunk streaming cache and working set management (Phase 6).
"""
import pytest
from strata.chunk_streaming import ChunkLRUCache


def test_lru_cache_initialization():
    cache = ChunkLRUCache(max_loaded_chunks=27, radius_x=1, radius_y=1, radius_z=1)
    assert cache.max_loaded_chunks == 27
    assert len(cache.get_loaded_chunks()) == 0


def test_working_set_chunks_calculation():
    cache = ChunkLRUCache(radius_x=1, radius_y=1, radius_z=1)
    chunks = cache.get_working_set_chunks((0, 0, 0))
    # 3 x 3 x 3 = 27 3D chunks
    assert len(chunks) == 27
    assert (0, 0, 0) in chunks
    assert (1, 1, 1) in chunks
    assert (-1, -1, -1) in chunks


def test_lru_touch_and_eviction():
    cache = ChunkLRUCache(max_loaded_chunks=5, radius_x=0, radius_y=0, radius_z=0)
    manifest = [(i, 0, 0) for i in range(10)]

    for i in range(5):
        to_load, to_unload = cache.update_working_set((i, 0, 0), manifest)
        assert len(to_unload) == 0

    assert len(cache.get_loaded_chunks()) == 5

    # Accessing 6th chunk should evict oldest unpinned chunk (0, 0, 0)
    to_load, to_unload = cache.update_working_set((5, 0, 0), manifest)
    assert (5, 0, 0) in to_load
    assert (0, 0, 0) in to_unload
    assert len(cache.get_loaded_chunks()) == 5


def test_chunk_pinning():
    cache = ChunkLRUCache(max_loaded_chunks=3, radius_x=0, radius_y=0, radius_z=0)
    manifest = [(i, 0, 0) for i in range(10)]

    # Load 3 chunks and pin chunk (0, 0, 0)
    for i in range(3):
        cache.update_working_set((i, 0, 0), manifest)
    cache.pin((0, 0, 0))

    # Accessing 4th chunk should evict chunk (1, 0, 0), NOT pinned chunk (0, 0, 0)
    to_load, to_unload = cache.update_working_set((3, 0, 0), manifest)
    assert (0, 0, 0) in cache.get_loaded_chunks()
    assert (1, 0, 0) in to_unload


def test_unload_all_unpinned():
    cache = ChunkLRUCache(max_loaded_chunks=10)
    manifest = [(i, 0, 0) for i in range(5)]
    cache.update_working_set((0, 0, 0), manifest)
    cache.pin((0, 0, 0))

    unloaded = cache.unload_all_unpinned()
    # Pinned chunk (0, 0, 0) remains loaded
    assert (0, 0, 0) not in unloaded
    assert cache.get_loaded_chunks() == [(0, 0, 0)]
