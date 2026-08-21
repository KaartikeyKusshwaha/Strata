"""Resolves prototype templates for requested block states using user library first,
falling back to own-library generator when allowed.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from strata.reference_profiles import get_asset_entry, get_combined_profile


def acquire_prototype_template(
    block_id: str,
    block_map: Dict[str, str],
    own_library_mode: bool = False,
    missing_asset_policy: str = "generate",
    reference_profile_name: str = "combined_v1",
) -> Optional[Dict[str, Any]]:
    """Resolves template metadata for a block ID.

    Precedence:
    1. Direct match in block_map (user library mapping)
    2. Exact canonical block_id match in reference profile
    3. Own-library generator template (if policy == 'generate' or own_library_mode == True)
    """
    # 1. User block map authority
    if block_id in block_map:
        return {
            "source": "user_library",
            "prototype_name": block_map[block_id],
            "block_id": block_id,
        }

    # 2. Reference profile lookup
    profile = get_combined_profile()
    entry = get_asset_entry(profile, block_id)
    if entry:
        return {
            "source": "reference_profile",
            "prototype_name": entry["object_name"],
            "block_id": block_id,
            "dimensions": entry.get("local_dimensions", [1.0, 1.0, 1.0]),
            "anchor": entry.get("normalized_cell_anchor", [0.0, 0.0, 0.0]),
        }

    # 3. Fallback generator
    if own_library_mode or missing_asset_policy == "generate":
        clean_name = block_id.split(":")[-1].replace("_", " ").title().replace(" ", "")
        return {
            "source": "generated",
            "prototype_name": clean_name,
            "block_id": block_id,
            "dimensions": [1.0, 1.0, 1.0],
            "anchor": [0.0, 0.0, 0.0],
        }

    return None
