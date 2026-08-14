"""Reference profile extraction script.

Runs Blender in background mode to inspect read-only reference .blend files
and write schema-compliant metadata profiles to strata/data/reference_profiles/.

Usage:
    blender --background --factory-startup --disable-autoexec --python scripts/extract_reference_profiles.py
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import bpy

# Define reference file paths according to PLAN.md §2
BOXSCAPE_FILES = [
    Path(r"C:\Users\LENONO\Downloads\boxscape-studios-assets-v45\Cycles_Minecraft_Rig BSS Edit V0.4.6\Minecraft_Blocks_Rig.blend"),
    Path(r"C:\Users\LENONO\Downloads\boxscape-studios-assets-v45\Cycles_Minecraft_Rig BSS Edit V0.4.6\New_Items_Blocks.blend"),
]

USER_ASSETS_FILE = Path(r"D:\Minecraft Animations\Projects\Animations\assets.blend")

OUTPUT_DIR = Path(__file__).parent.parent / "strata" / "data" / "reference_profiles"


def compute_file_hash(filepath: Path) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def extract_file_metadata(filepath: Path) -> dict:
    return {
        "filename": filepath.name,
        "path": str(filepath),
        "sha256": compute_file_hash(filepath),
        "size_bytes": filepath.stat().st_size,
    }


def inspect_current_blend(profile_kind: str) -> dict:
    """Inspects currently loaded Blender mainfile for block & asset metadata."""
    assets = {}

    for obj in bpy.data.objects:
        # Determine material slots
        material_slots = [
            slot.material.name for slot in obj.material_slots if slot.material
        ]

        # Determine hierarchy parts
        hierarchy_parts = [child.name for child in obj.children]

        # Determine armature info if applicable
        armature_bones = []
        if obj.type == "ARMATURE" and obj.data:
            armature_bones = [bone.name for bone in obj.data.bones]
        elif obj.type == "MESH":
            for mod in obj.modifiers:
                if mod.type == "ARMATURE" and mod.object and mod.object.data:
                    armature_bones = [bone.name for bone in mod.object.data.bones]

        # Vertex groups
        vertex_groups = [vg.name for vg in obj.vertex_groups]

        # Constraints
        constraints = [c.name for c in obj.constraints]

        # Dimensions & Anchor calculation
        dims = [round(float(d), 4) for d in obj.dimensions]
        anchor = [round(float(loc), 4) for loc in obj.location]

        # Format block ID / name key
        name_key = obj.name
        mc_alias = f"minecraft:{obj.name.lower().replace(' ', '_')}"

        assets[name_key] = {
            "object_name": obj.name,
            "object_type": obj.type,
            "local_dimensions": dims,
            "normalized_cell_anchor": anchor,
            "material_slots": material_slots,
            "hierarchy_parts": hierarchy_parts,
            "armature_bones": armature_bones,
            "vertex_groups": vertex_groups,
            "constraints": constraints,
            "recommended_motion_pivot": None,
            "aliases": [name_key, mc_alias],
            "source_profile": profile_kind,
        }

    return assets


def build_profile(files: list[Path], profile_kind: str) -> dict:
    file_metas = []
    combined_assets = {}

    for filepath in files:
        if not filepath.exists():
            print(f"WARNING: Reference file not found: {filepath}")
            continue

        file_metas.append(extract_file_metadata(filepath))
        print(f"Inspecting {filepath.name}...")
        bpy.ops.wm.open_mainfile(filepath=str(filepath))

        assets = inspect_current_blend(profile_kind)
        combined_assets.update(assets)

    return {
        "schema_version": 1,
        "profile_name": profile_kind,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_files": file_metas,
        "assets": combined_assets,
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Extracting boxscape_v046 profile...")
    boxscape_profile = build_profile(BOXSCAPE_FILES, "boxscape_v046")
    boxscape_out = OUTPUT_DIR / "boxscape_v046.json"
    with open(boxscape_out, "w", encoding="utf-8") as f:
        json.dump(boxscape_profile, f, indent=2)
    print(f"Wrote {boxscape_out} ({len(boxscape_profile['assets'])} assets)")

    print("Extracting user_assets_v1 profile...")
    user_assets_profile = build_profile([USER_ASSETS_FILE], "user_assets_v1")
    user_out = OUTPUT_DIR / "user_assets_v1.json"
    with open(user_out, "w", encoding="utf-8") as f:
        json.dump(user_assets_profile, f, indent=2)
    print(f"Wrote {user_out} ({len(user_assets_profile['assets'])} assets)")

    # Build combined_v1 profile (user assets take priority over Boxscape)
    print("Building combined_v1 profile...")
    combined_assets = {}
    # 1. Boxscape base
    for key, val in boxscape_profile["assets"].items():
        combined_assets[key] = val.copy()
    # 2. User assets override/extend
    for key, val in user_assets_profile["assets"].items():
        combined_assets[key] = val.copy()

    combined_sources = boxscape_profile["source_files"] + user_assets_profile["source_files"]

    combined_profile = {
        "schema_version": 1,
        "profile_name": "combined_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_files": combined_sources,
        "assets": combined_assets,
    }

    combined_out = OUTPUT_DIR / "combined_v1.json"
    with open(combined_out, "w", encoding="utf-8") as f:
        json.dump(combined_profile, f, indent=2)
    print(f"Wrote {combined_out} ({len(combined_profile['assets'])} assets)")
    print("Profile extraction complete.")


if __name__ == "__main__":
    main()
