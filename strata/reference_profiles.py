"""Runtime loader and validator for reference profile JSON artifacts.

Reference profiles store metadata (object names, dimensions, anchors, material slots,
rig bones) extracted from reference .blend files without containing any mesh geometry
or texture data.
"""
import json
from pathlib import Path
from typing import Optional, Dict, Any

PROFILES_DIR = Path(__file__).parent / "data" / "reference_profiles"


def load_profile(name: str) -> Dict[str, Any]:
    """Loads a reference profile JSON by name (e.g. 'combined_v1')."""
    filepath = PROFILES_DIR / f"{name}.json"
    if not filepath.exists():
        raise FileNotFoundError(f"Reference profile not found: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    validate_profile_schema(data)
    return data


def get_combined_profile() -> Dict[str, Any]:
    """Shortcut to load the default combined_v1 reference profile."""
    return load_profile("combined_v1")


def validate_profile_schema(data: Dict[str, Any]) -> bool:
    """Validates that a dictionary conforms to the reference profile schema."""
    required_keys = {"schema_version", "profile_name", "generated_at", "source_files", "assets"}
    missing = required_keys - set(data.keys())
    if missing:
        raise ValueError(f"Invalid profile schema, missing required keys: {missing}")

    if data["schema_version"] != 1:
        raise ValueError(f"Unsupported profile schema_version: {data['schema_version']}")

    if not isinstance(data["source_files"], list) or not data["source_files"]:
        raise ValueError("Profile source_files must be a non-empty list")

    for src in data["source_files"]:
        if "sha256" not in src or not src["sha256"]:
            raise ValueError(f"Source file entry missing sha256: {src}")

    return True


def get_asset_entry(profile: Dict[str, Any], block_id: str) -> Optional[Dict[str, Any]]:
    """Finds an asset entry in the profile by block ID or alias."""
    assets = profile.get("assets", {})
    # 1. Direct match by exact key
    if block_id in assets:
        return assets[block_id]

    # 2. Match by alias or object_name
    block_id_lower = block_id.lower()
    for entry in assets.values():
        if entry.get("object_name", "").lower() == block_id_lower:
            return entry
        aliases = [a.lower() for a in entry.get("aliases", [])]
        if block_id_lower in aliases:
            return entry

    return None
