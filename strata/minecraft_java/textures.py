"""Resolves texture variable references and extracts image bytes from texture pack ZIPs or JARs.
"""
from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Dict, List, Optional


def resolve_texture_variable(var_name: str, texture_map: Dict[str, str]) -> str:
    """Recursively resolves texture variable references (e.g. '#all' -> 'block/stone')."""
    visited = set()
    current = var_name

    while current.startswith("#"):
        key = current[1:]
        if key in visited:
            break
        visited.add(key)
        if key in texture_map:
            current = texture_map[key]
        else:
            break

    return current


def extract_texture_image(
    texture_ref: str,
    texture_sources: List[Any],
) -> Optional[bytes]:
    """Resolves texture reference path (e.g. 'minecraft:block/stone' or 'block/stone')
    against the list of TextureSource objects (user_pack -> selected_pack -> minecraft_jar).
    """
    clean_ref = texture_ref
    if clean_ref.startswith("minecraft:"):
        clean_ref = clean_ref[len("minecraft:") :]

    # Canonical zip internal path: assets/minecraft/textures/<ref>.png
    internal_path = f"assets/minecraft/textures/{clean_ref}.png"

    for src in texture_sources:
        pack_path = getattr(src, "path", str(src))
        if not pack_path or not os.path.exists(pack_path):
            continue

        p = Path(pack_path)
        if p.is_dir():
            target_file = p / internal_path
            if target_file.exists():
                return target_file.read_bytes()
        elif p.is_file() and p.suffix.lower() in (".zip", ".jar"):
            try:
                with zipfile.ZipFile(p, "r") as zf:
                    if internal_path in zf.namelist():
                        return zf.read(internal_path)
            except zipfile.BadZipFile:
                continue

    return None
