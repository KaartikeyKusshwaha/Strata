"""Blender-side paging helper for chunk collection loading, unloading, and mesh duplication.
"""
import os
import bpy
from .chunk_utils import parse_chunk_name


def load_chunk_collection(chunk_name: str, blend_path: str) -> bool:
    """Links or appends a chunk collection from an external chunks/Chunk_*.blend file into Blender."""
    if not blend_path or not os.path.exists(blend_path):
        return False

    if chunk_name in bpy.data.collections:
        return True

    with bpy.data.libraries.load(blend_path, link=True) as (data_from, data_to):
        if chunk_name in data_from.collections:
            data_to.collections = [chunk_name]

    coll = bpy.data.collections.get(chunk_name)
    if coll:
        # Link to chunks parent or scene collection
        parent = bpy.data.collections.get("MC_Chunks_16x16x16") or bpy.context.scene.collection
        if coll.name not in parent.children:
            parent.children.link(coll)
        return True
    return False


def unload_chunk_collection(chunk_name: str) -> bool:
    """Unlinks and removes a chunk collection and its local objects, then purges orphaned datablocks."""
    coll = bpy.data.collections.get(chunk_name)
    if coll is None:
        return False

    # Unlink and remove objects
    for obj in list(coll.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

    bpy.data.collections.remove(coll, do_unlink=True)

    # Purge orphans recursively
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    return True


def make_selected_mesh_unique() -> int:
    """Duplicates mesh datablocks only for explicitly selected static block objects."""
    count = 0
    for obj in bpy.context.selected_objects:
        if obj.type == "MESH" and obj.data:
            if obj.data.users > 1:
                obj.data = obj.data.copy()
                count += 1
    return count
