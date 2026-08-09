"""Water body builder.

Supports both daytime and nighttime water material/mesh setups extracted from A1.blend
and nightime.blend. Sends commands over blender_io bridge (no bpy imports).
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Dict, Tuple

from .. import blender_io


@dataclass
class WaterConfig:
    mode: str = "day"  # "day" or "night"
    collection_name: str = "P1 Water"
    object_name: str = "A1_Water_Single_Mesh"
    material_name: str = "A1 WORLD_1 Water Surface"
    location: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    dimensions: Tuple[float, float, float] = (386.0, 400.0, 38.0)
    
    # Daytime water defaults (from A1.blend)
    day_base_color: Tuple[float, float, float, float] = (0.01, 0.17, 0.34, 1.0)
    day_roughness: float = 0.19
    day_ior: float = 1.333
    day_coat_weight: float = 0.28
    day_coat_roughness: float = 0.12
    day_coat_ior: float = 1.5
    day_noise_scale: float = 0.18
    day_noise_detail: float = 2.0
    day_noise_roughness: float = 0.45
    day_bump_strength: float = 0.055
    day_bump_distance: float = 0.055
    
    # Nighttime water defaults (from nightime.blend)
    night_base_color: Tuple[float, float, float, float] = (0.006, 0.03, 0.08, 1.0)
    night_roughness: float = 0.22
    night_ior: float = 1.333
    night_coat_weight: float = 0.14
    night_coat_roughness: float = 0.18
    night_coat_ior: float = 1.5
    night_noise_scale: float = 0.35
    night_noise_detail: float = 2.0
    night_noise_roughness: float = 0.40
    night_bump_strength: float = 0.080
    night_bump_distance: float = 0.120


def build_water(config: WaterConfig | None = None) -> Dict[str, object]:
    """Sends build_water command over the bridge."""
    if config is None:
        config = WaterConfig()
    return blender_io.call("build_water", **dataclasses.asdict(config))
