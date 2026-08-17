"""Library sources, texture priority stack, and preflight build estimation.

No bpy required at module scope.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Literal, Optional, Tuple, Set


NON_BLOCK_ASSET_KEYWORDS = {
    "steve", "alex", "player", "zombie", "skeleton", "creeper",
    "spider", "cow", "pig", "sheep", "villager", "armour_stand",
    "armor_stand", "rig", "hero"
}


@dataclass
class TextureSource:
    kind: Literal["user_pack", "selected_pack", "minecraft_jar"]
    path: str
    sha256: str = ""


@dataclass
class BuildEstimate:
    total_blocks: int = 0
    visible_blocks: int = 0
    total_chunks: int = 0
    static_object_count: int = 0
    rig_root_count: int = 0
    missing_assets: List[str] = field(default_factory=list)
    texture_sources: List[Dict[str, str]] = field(default_factory=list)
    missing_asset_policy: str = "generate"


def compute_file_sha256(filepath: str) -> str:
    path = Path(filepath)
    if not path.exists() or not path.is_file():
        return ""
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def resolve_texture_stack(
    minecraft_jar: str = "",
    user_texture_packs: Tuple[str, ...] = (),
    selected_texture_packs: Tuple[str, ...] = (),
) -> List[TextureSource]:
    """Resolves texture stack precedence: user_packs (1st) -> selected_packs (2nd) -> minecraft_jar (3rd)."""
    stack: List[TextureSource] = []

    for pack_path in user_texture_packs:
        if pack_path:
            sha = compute_file_sha256(pack_path)
            stack.append(TextureSource(kind="user_pack", path=pack_path, sha256=sha))

    for pack_path in selected_texture_packs:
        if pack_path:
            sha = compute_file_sha256(pack_path)
            stack.append(TextureSource(kind="selected_pack", path=pack_path, sha256=sha))

    if minecraft_jar:
        sha = compute_file_sha256(minecraft_jar)
        stack.append(TextureSource(kind="minecraft_jar", path=minecraft_jar, sha256=sha))

    return stack


def filter_non_block_assets(candidate_names: Iterable[str]) -> Tuple[List[str], List[str]]:
    """Filters object candidate names into (valid_block_assets, ignored_non_block_assets)."""
    valid_blocks = []
    ignored_assets = []

    for name in candidate_names:
        name_lower = name.lower()
        if any(kw in name_lower for kw in NON_BLOCK_ASSET_KEYWORDS):
            ignored_assets.append(name)
        else:
            valid_blocks.append(name)

    return valid_blocks, ignored_assets
