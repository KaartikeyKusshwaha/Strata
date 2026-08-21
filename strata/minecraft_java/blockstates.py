"""Parses Minecraft Java blockstate JSON files.

Supports variants (with weighted random selection via deterministic hashing) and multipart clauses.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple


def _hash_coords(x: int, y: int, z: int) -> int:
    """Deterministic hash for coordinate-based variant selection."""
    return (x * 73856093 ^ y * 19349663 ^ z * 83492791) & 0x7FFFFFFF


def parse_blockstate_json(
    json_content: str,
    mc_x: int = 0,
    mc_y: int = 0,
    mc_z: int = 0,
    state_properties: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """Parses a Java blockstate JSON payload and returns selected model references with transforms.

    Returns a list of dicts:
    [
        {
            "model": "minecraft:block/cube_all",
            "x": 0,  # X rotation in deg
            "y": 90, # Y rotation in deg
            "uvlock": False
        }
    ]
    """
    data = json.loads(json_content)
    selected_models: List[Dict[str, Any]] = []

    if "variants" in data:
        variants = data["variants"]
        # Match variant key (e.g. "facing=north,half=lower" or "" or "normal")
        target_variant = None
        if "" in variants:
            target_variant = variants[""]
        elif "normal" in variants:
            target_variant = variants["normal"]
        elif state_properties:
            # Build prop string
            prop_str = ",".join(f"{k}={v}" for k, v in sorted(state_properties.items()))
            if prop_str in variants:
                target_variant = variants[prop_str]

        if target_variant is None and variants:
            # Fallback to first available variant
            target_variant = next(iter(variants.values()))

        if target_variant:
            if isinstance(target_variant, list):
                # Weighted selection via coordinate hash
                coord_hash = _hash_coords(mc_x, mc_y, mc_z)
                idx = coord_hash % len(target_variant)
                chosen = target_variant[idx]
            else:
                chosen = target_variant

            selected_models.append({
                "model": chosen.get("model", ""),
                "x": chosen.get("x", 0),
                "y": chosen.get("y", 0),
                "uvlock": chosen.get("uvlock", False),
            })

    elif "multipart" in data:
        for clause in data["multipart"]:
            apply_clause = True
            if "when" in clause and state_properties:
                when = clause["when"]
                # OR condition
                if "OR" in when:
                    apply_clause = any(
                        all(state_properties.get(k) == str(v) for k, v in cond.items())
                        for cond in when["OR"]
                    )
                else:
                    apply_clause = all(
                        state_properties.get(k) == str(v) for k, v in when.items()
                    )

            if apply_clause and "apply" in clause:
                apply_data = clause["apply"]
                if isinstance(apply_data, list):
                    chosen = apply_data[0]
                else:
                    chosen = apply_data

                selected_models.append({
                    "model": chosen.get("model", ""),
                    "x": chosen.get("x", 0),
                    "y": chosen.get("y", 0),
                    "uvlock": chosen.get("uvlock", False),
                })

    return selected_models
