"""Tests for reference profiles (Phase 0).

Validates schema version, source file hashes, profile loading, asset lookup,
and confirms NO mesh geometry or texture byte data was checked into JSON.
"""
import pytest
from strata.reference_profiles import (
    load_profile,
    get_combined_profile,
    validate_profile_schema,
    get_asset_entry,
)


def test_boxscape_profile_exists_and_loads():
    profile = load_profile("boxscape_v046")
    assert profile["profile_name"] == "boxscape_v046"
    assert profile["schema_version"] == 1
    assert len(profile["assets"]) > 0


def test_user_assets_profile_exists_and_loads():
    profile = load_profile("user_assets_v1")
    assert profile["profile_name"] == "user_assets_v1"
    assert profile["schema_version"] == 1
    assert len(profile["assets"]) > 0


def test_combined_profile_exists_and_loads():
    profile = get_combined_profile()
    assert profile["profile_name"] == "combined_v1"
    assert profile["schema_version"] == 1
    assert len(profile["assets"]) > 0


def test_source_hashes_are_present():
    for name in ["boxscape_v046", "user_assets_v1", "combined_v1"]:
        profile = load_profile(name)
        assert len(profile["source_files"]) > 0
        for src in profile["source_files"]:
            assert "sha256" in src
            assert len(src["sha256"]) == 64  # valid SHA-256 hex string


def _check_no_forbidden_keys(data, forbidden_keys):
    if isinstance(data, dict):
        for k, v in data.items():
            assert k.lower() not in forbidden_keys, f"Forbidden key found in JSON: {k}"
            _check_no_forbidden_keys(v, forbidden_keys)
    elif isinstance(data, list):
        for item in data:
            _check_no_forbidden_keys(item, forbidden_keys)


def test_no_mesh_vertex_data_in_profiles():
    forbidden = {"vertices", "edges", "faces", "polygons", "loops", "uv_layers", "mesh_data"}
    for name in ["boxscape_v046", "user_assets_v1", "combined_v1"]:
        profile = load_profile(name)
        _check_no_forbidden_keys(profile, forbidden)


def test_no_texture_bytes_in_profiles():
    forbidden = {"pixels", "image_data", "texture_bytes", "binary_data"}
    for name in ["boxscape_v046", "user_assets_v1", "combined_v1"]:
        profile = load_profile(name)
        _check_no_forbidden_keys(profile, forbidden)


def test_combined_prefers_user_assets():
    combined = get_combined_profile()
    user_assets = load_profile("user_assets_v1")
    # For any asset key present in user_assets, combined profile should have source_profile == user_assets_v1
    for key in user_assets["assets"]:
        assert key in combined["assets"]
        assert combined["assets"][key]["source_profile"] == "user_assets_v1"


def test_get_asset_entry_lookup():
    combined = get_combined_profile()
    sample_key = list(combined["assets"].keys())[0]
    entry = get_asset_entry(combined, sample_key)
    assert entry is not None
    assert entry["object_name"] == combined["assets"][sample_key]["object_name"]
