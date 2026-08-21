"""World manifest serialization and chunk boundary calculations.

Schema matching PLAN.md Section 3 contract.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ChunkManifestEntry:
    name: str
    file: str  # Relative path e.g. "chunks/Chunk_xp000_yp000_zp000.blend"
    block_count: int = 0
    static_object_count: int = 0
    rig_root_count: int = 0
    bounds_minecraft: List[int] = field(default_factory=list)  # [x_min, y_min, z_min, x_max, y_max, z_max]


@dataclass
class WorldManifest:
    schema_version: int = 1
    chunk_size: int = 16
    coordinate_mapping: str = "minecraft_xyz_to_blender_xzy"
    prototype_library: str = "Strata_PrototypeLibrary.blend"
    missing_asset_policy: str = "generate"
    texture_sources: List[Dict[str, Any]] = field(default_factory=list)
    chunks: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # "cx:cy:cz" -> entry dict


def compute_chunk_bounds(cx: int, cy: int, cz: int, chunk_size: int = 16) -> List[int]:
    """Calculates min and max Minecraft bounding coordinates for a 3D chunk.

    Returns [x_min, y_min, z_min, x_max, y_max, z_max].
    """
    x_min = cx * chunk_size
    y_min = cy * chunk_size
    z_min = cz * chunk_size
    x_max = x_min + chunk_size - 1
    y_max = y_min + chunk_size - 1
    z_max = z_min + chunk_size - 1
    return [x_min, y_min, z_min, x_max, y_max, z_max]


def save_manifest(output_dir: str, manifest: WorldManifest) -> str:
    out_path = Path(output_dir) / "strata-world-manifest.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(asdict(manifest), f, indent=2)
    return str(out_path)


def load_manifest(output_dir: str) -> WorldManifest:
    in_path = Path(output_dir) / "strata-world-manifest.json"
    if not in_path.exists():
        raise FileNotFoundError(f"World manifest not found: {in_path}")
    with open(in_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return WorldManifest(
        schema_version=data.get("schema_version", 1),
        chunk_size=data.get("chunk_size", 16),
        coordinate_mapping=data.get("coordinate_mapping", "minecraft_xyz_to_blender_xzy"),
        prototype_library=data.get("prototype_library", "Strata_PrototypeLibrary.blend"),
        missing_asset_policy=data.get("missing_asset_policy", "generate"),
        texture_sources=data.get("texture_sources", []),
        chunks=data.get("chunks", {}),
    )
