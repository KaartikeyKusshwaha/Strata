"""Stage 5 helper: pure 3D chunk math, A1 chunk name formatting, and coordinate mapping.

No bpy, no I/O, no third-party deps.
"""
from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Dict, Iterable, Tuple

from .pipeline_state import Block, ChunkContents, ChunkKey, ChunkKey3D

A1_CHUNK_NAME_REGEX = re.compile(
    r"^Chunk_x([pm])(\d+)_y([pm])(\d+)_z([pm])(\d+)$", re.IGNORECASE
)


def format_a1_chunk_name(cx: int, cy: int, cz: int) -> str:
    """Formats a 3D chunk coordinate into the A1 reference convention.

    Examples:
        format_a1_chunk_name(0, 0, 0) -> "Chunk_xp000_yp000_zp000"
        format_a1_chunk_name(1, -2, 3) -> "Chunk_xp001_ym002_zp003"
        format_a1_chunk_name(-15, 0, 120) -> "Chunk_xm015_yp000_zp120"
    """
    def _format_comp(prefix: str, val: int) -> str:
        sign = "m" if val < 0 else "p"
        mag = abs(val)
        return f"{prefix}{sign}{mag:03d}"

    return f"Chunk_{_format_comp('x', cx)}_{_format_comp('y', cy)}_{_format_comp('z', cz)}"


def parse_a1_chunk_name(name: str) -> Tuple[int, int, int]:
    """Parses an A1 chunk name back into integer 3D chunk coordinates (cx, cy, cz)."""
    match = A1_CHUNK_NAME_REGEX.match(name.strip())
    if not match:
        raise ValueError(f"Invalid A1 chunk name format: {name!r}")

    x_sign, x_val, y_sign, y_val, z_sign, z_val = match.groups()
    cx = -int(x_val) if x_sign.lower() == "m" else int(x_val)
    cy = -int(y_val) if y_sign.lower() == "m" else int(y_val)
    cz = -int(z_val) if z_sign.lower() == "m" else int(z_val)

    return (cx, cy, cz)


def mc_to_blender_coords(mc_x: int, mc_y: int, mc_z: int) -> Tuple[int, int, int]:
    """Maps Minecraft coordinates (x, y, z) to Blender coordinates (x, z, y).

    In Minecraft, Y is vertical height. In Blender, Z is vertical height.
    """
    return (int(mc_x), int(mc_z), int(mc_y))


def bucket_into_3d_chunks(
    blocks: Iterable[Block], chunk_size: int = 16
) -> Dict[ChunkKey3D, ChunkContents]:
    """Groups (x, y, z, block_id) tuples into 3D chunks (cx, cy, cz),
    then by block_id within each chunk."""
    chunks: Dict[ChunkKey3D, Dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for item in blocks:
        mc_x, mc_y, mc_z, block_id = item[0], item[1], item[2], item[3]
        cx = math.floor(mc_x / chunk_size)
        cy = math.floor(mc_y / chunk_size)
        cz = math.floor(mc_z / chunk_size)
        key = (cx, cy, cz)
        chunks[key][block_id].append((mc_x, mc_y, mc_z))
    return {k: dict(v) for k, v in chunks.items()}


def bucket_into_chunks(
    blocks: Iterable[Block], chunk_size: int = 16
) -> Dict[ChunkKey, ChunkContents]:
    """Legacy 2D grouping helper for backward compatibility."""
    chunks: Dict[ChunkKey, Dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for item in blocks:
        mc_x, mc_y, mc_z, block_id = item[0], item[1], item[2], item[3]
        cx = math.floor(mc_x / chunk_size)
        cz = math.floor(mc_z / chunk_size)
        key = (cx, cz)
        chunks[key][block_id].append((mc_x, mc_y, mc_z))
    return {k: dict(v) for k, v in chunks.items()}
