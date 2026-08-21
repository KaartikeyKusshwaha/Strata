"""Parses Java block model JSON files and resolves parent model inheritance chains,
texture variable mappings, and 3D cube elements.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class ResolvedModel:
    parent: Optional[str] = None
    ambientocclusion: bool = True
    textures: Dict[str, str] = field(default_factory=dict)
    elements: List[Dict[str, Any]] = field(default_factory=list)


def parse_model_json(
    json_content: str,
    parent_resolver: Optional[Callable[[str], str]] = None,
) -> ResolvedModel:
    """Parses a Java model JSON string and recursively merges parent model chains."""
    data = json.loads(json_content)

    parent_ref = data.get("parent")
    textures = data.get("textures", {}).copy()
    elements = data.get("elements", []).copy()
    ambientocclusion = data.get("ambientocclusion", True)

    if parent_ref and parent_resolver:
        parent_json = parent_resolver(parent_ref)
        if parent_json:
            parent_model = parse_model_json(parent_json, parent_resolver=parent_resolver)
            # Parent textures are overridden by child textures
            merged_textures = parent_model.textures.copy()
            merged_textures.update(textures)
            textures = merged_textures

            # If child specifies no elements, inherit parent elements
            if not elements:
                elements = parent_model.elements

            ambientocclusion = data.get("ambientocclusion", parent_model.ambientocclusion)

    return ResolvedModel(
        parent=parent_ref,
        ambientocclusion=ambientocclusion,
        textures=textures,
        elements=elements,
    )


def element_to_blender_box(element: Dict[str, Any]) -> Dict[str, Any]:
    """Converts a Minecraft Java 16x16x16 coordinate element into Blender Z-up unit coordinates.

    In Java Minecraft:
    - [x, y, z] in range 0..16
    - Y is vertical height (0 = bottom, 16 = top)
    - X is east/west (0 = west, 16 = east)
    - Z is north/south (0 = north, 16 = south)

    In Blender:
    - X is east/west (0..1)
    - Z is vertical height (0..1)
    - Y is north/south (0..1)
    """
    from_pos = element.get("from", [0, 0, 0])
    to_pos = element.get("to", [16, 16, 16])

    # Convert 0..16 coordinates to 0.0..1.0 unit scale
    mc_x1, mc_y1, mc_z1 = from_pos[0] / 16.0, from_pos[1] / 16.0, from_pos[2] / 16.0
    mc_x2, mc_y2, mc_z2 = to_pos[0] / 16.0, to_pos[1] / 16.0, to_pos[2] / 16.0

    blender_min = (min(mc_x1, mc_x2), min(mc_z1, mc_z2), min(mc_y1, mc_y2))
    blender_max = (max(mc_x1, mc_x2), max(mc_z1, mc_z2), max(mc_y1, mc_y2))

    rotation = element.get("rotation", {})
    faces = element.get("faces", {})

    return {
        "min": blender_min,
        "max": blender_max,
        "rotation": rotation,
        "faces": faces,
    }
