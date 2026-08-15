"""
Bridge commands invoked BY the pipeline stages running outside Blender.

This is the file that imports strata.plugins.geometry_backends /
render_targets directly, because it runs inside Blender's Python -- see the
bpy boundary note in strata/stages/__init__.py (8.24): external-process
stage code must never import these; this file is where that boundary is
actually crossed, on purpose, in one place.
"""
from __future__ import annotations

import bpy

from .. import bridge_server


def _ensure_prototypes_linked(library_blend_path, candidate_names):
    proto_collection = bpy.data.collections.get("Strata_Prototypes")
    if proto_collection is None:
        proto_collection = bpy.data.collections.new("Strata_Prototypes")
        bpy.context.scene.collection.children.link(proto_collection)
        proto_collection.hide_viewport = True
        proto_collection.hide_render = True

    to_link = [n for n in candidate_names if n and n not in bpy.data.objects]
    if to_link:
        with bpy.data.libraries.load(library_blend_path, link=True) as (data_from, data_to):
            data_to.objects = [n for n in data_from.objects if n in to_link]

    linked = {}
    for name in candidate_names:
        obj = bpy.data.objects.get(name) if name else None
        if obj is None:
            continue
        if obj.name not in proto_collection.objects:
            proto_collection.objects.link(obj)
        linked[name] = obj
    return linked


@bridge_server.register_command("list_block_library")
def list_block_library(library_blend_path):
    """Peeks at a .blend's top-level object names without linking anything
    -- cheap, safe to call before committing to a real import."""
    with bpy.data.libraries.load(library_blend_path, link=True) as (data_from, _data_to):
        names = list(data_from.objects)
    return {"object_names": sorted(names)}


@bridge_server.register_command("build_geometry")
def build_geometry(library_blend_path, groups, backend_name="geometry_nodes"):
    from strata.plugins.base import discover
    from strata.plugins.geometry_backends.geometry_nodes_backend import GeometryNodesBackend
    from strata.chunking import format_a1_chunk_name

    backends = {"geometry_nodes": GeometryNodesBackend, **discover("geometry_backends")}
    backend_cls = backends.get(backend_name)
    if backend_cls is None:
        raise ValueError(f"No geometry_backends plugin named {backend_name!r}. Available: {sorted(backends)}")
    backend = backend_cls()

    candidate_names = sorted({g["prototype_name"] for g in groups if g["prototype_name"]})
    prototypes = _ensure_prototypes_linked(library_blend_path, candidate_names)

    # 1. World root collection
    world_root = bpy.data.collections.get("MC_Chunked_IndividualWorld")
    if world_root is None:
        world_root = bpy.data.collections.get("Strata_World")
    if world_root is None:
        world_root = bpy.data.collections.new("MC_Chunked_IndividualWorld")
        bpy.context.scene.collection.children.link(world_root)

    # 2. Chunks parent collection
    chunks_parent = bpy.data.collections.get("MC_Chunks_16x16x16")
    if chunks_parent is None:
        chunks_parent = bpy.data.collections.new("MC_Chunks_16x16x16")
        world_root.children.link(chunks_parent)

    unmapped = set()
    block_count = 0
    chunk_names = set()
    chunk_block_counts = {}

    for group in groups:
        cx = group.get("chunk_x")
        cy = group.get("chunk_y", 0)
        cz = group.get("chunk_z")

        if cx is None or cz is None:
            parts = group["chunk_key"].split(":")
            cx = int(parts[0])
            if len(parts) >= 3:
                cy = int(parts[1])
                cz = int(parts[2])
            else:
                cz = int(parts[1])

        chunk_name = group.get("chunk_name") or format_a1_chunk_name(cx, cy, cz)
        chunk_names.add(chunk_name)

        chunk_collection = bpy.data.collections.get(chunk_name)
        if chunk_collection is None:
            chunk_collection = bpy.data.collections.new(chunk_name)
            chunks_parent.children.link(chunk_collection)

            # Set A1 metadata custom properties
            chunk_collection["mc_chunk_size"] = 16
            chunk_collection["mc_chunk_x"] = cx
            chunk_collection["mc_chunk_y"] = cy
            chunk_collection["mc_chunk_z"] = cz
            chunk_collection["mc_kind"] = "chunk"
            chunk_collection["minecraft_chunk"] = 1

        proto_obj = prototypes.get(group["prototype_name"])
        if proto_obj is None:
            unmapped.add(group["block_id"])
            continue

        positions = [tuple(p) for p in group["positions"]]
        backend.place_instances(
            chunk_collection, proto_obj, positions,
            name_hint=f"{chunk_name}_{group['block_id']}",
        )
        placed = len(positions)
        block_count += placed
        chunk_block_counts[chunk_name] = chunk_block_counts.get(chunk_name, 0) + placed

    # Update mc_object_count on chunk collections
    for cname, count in chunk_block_counts.items():
        ccoll = bpy.data.collections.get(cname)
        if ccoll:
            ccoll["mc_object_count"] = count

    return {"chunks": len(chunk_names), "blocks_placed": block_count, "unmapped_block_ids": sorted(unmapped)}


@bridge_server.register_command("apply_render_target")
def apply_render_target(target_name="eevee_cycles"):
    from strata.plugins.base import discover
    from strata.plugins.render_targets.eevee_cycles import EeveeCyclesTarget

    targets = {"eevee_cycles": EeveeCyclesTarget, **discover("render_targets")}
    target_cls = targets.get(target_name)
    if target_cls is None:
        raise ValueError(f"No render_targets plugin named {target_name!r}. Available: {sorted(targets)}")
    target_cls().apply(bpy.context.scene)
    return {"applied": target_name}


@bridge_server.register_command("save_scene")
def save_scene(output_blend_path):
    bpy.ops.wm.save_as_mainfile(filepath=output_blend_path)
    return {"saved": output_blend_path}
