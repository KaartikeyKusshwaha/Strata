"""Unit tests for world manifest, chunk boundaries, and external chunk directory structure (Phase 5).
"""
import pytest
from strata import Pipeline
from strata.chunk_manifest import (
    ChunkManifestEntry,
    WorldManifest,
    compute_chunk_bounds,
    load_manifest,
    save_manifest,
)


def test_compute_chunk_bounds():
    b0 = compute_chunk_bounds(0, 0, 0, chunk_size=16)
    assert b0 == [0, 0, 0, 15, 15, 15]

    b1 = compute_chunk_bounds(1, -2, 3, chunk_size=16)
    assert b1 == [16, -32, 48, 31, -17, 63]


def test_world_manifest_save_and_load(tmp_path):
    manifest = WorldManifest(
        schema_version=1,
        chunk_size=16,
        missing_asset_policy="generate",
        texture_sources=[{"kind": "user_pack", "path": "pack.zip", "sha256": "abc12345"}],
        chunks={
            "0:0:0": {
                "name": "Chunk_xp000_yp000_zp000",
                "file": "chunks/Chunk_xp000_yp000_zp000.blend",
                "block_count": 100,
                "static_object_count": 100,
                "rig_root_count": 0,
                "bounds_minecraft": [0, 0, 0, 15, 15, 15],
            }
        },
    )

    out_file = save_manifest(str(tmp_path), manifest)
    assert "strata-world-manifest.json" in out_file

    loaded = load_manifest(str(tmp_path))
    assert loaded.schema_version == 1
    assert loaded.chunk_size == 16
    assert "0:0:0" in loaded.chunks
    assert loaded.chunks["0:0:0"]["name"] == "Chunk_xp000_yp000_zp000"


def test_manifest_relative_paths(tmp_path):
    manifest = WorldManifest()
    save_manifest(str(tmp_path), manifest)

    manifest_path = tmp_path / "strata-world-manifest.json"
    content = manifest_path.read_text(encoding="utf-8")
    assert "Strata_PrototypeLibrary.blend" in content


def test_pipeline_build_chunked_world_writes_manifest(tmp_path):
    p = Pipeline()
    p.build_chunked_world(str(tmp_path))

    manifest_path = tmp_path / "strata-world-manifest.json"
    assert manifest_path.exists()

    loaded = load_manifest(str(tmp_path))
    assert loaded.schema_version == 1
    assert p.state.stats["chunked_world_directory"] == str(tmp_path)
