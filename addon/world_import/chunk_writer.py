"""Blender-side single-chunk file writer.

Builds a single chunk collection, saves it to chunks/Chunk_*.blend,
and purges local orphaned data from Blender memory to keep builds memory-bounded.
"""
import os
import bpy
from .. import bridge_server


@bridge_server.register_command("build_chunk_file")
def build_chunk_file(chunk_info: dict):
    output_dir = chunk_info.get("output_dir", "")
    chunk_name = chunk_info.get("name", "Chunk_xp000_yp000_zp000")
    relative_file = chunk_info.get("file", f"chunks/{chunk_name}.blend")

    full_chunk_path = os.path.join(output_dir, relative_file)
    os.makedirs(os.path.dirname(full_chunk_path), exist_ok=True)

    # 1. Create or get chunk collection
    chunk_coll = bpy.data.collections.get(chunk_name)
    if chunk_coll is None:
        chunk_coll = bpy.data.collections.new(chunk_name)
        bpy.context.scene.collection.children.link(chunk_coll)

    # Set metadata
    chunk_coll["mc_chunk_size"] = chunk_info.get("chunk_size", 16)
    chunk_coll["mc_chunk_x"] = chunk_info.get("cx", 0)
    chunk_coll["mc_chunk_y"] = chunk_info.get("cy", 0)
    chunk_coll["mc_chunk_z"] = chunk_info.get("cz", 0)
    chunk_coll["mc_kind"] = "chunk"
    chunk_coll["mc_object_count"] = chunk_info.get("block_count", 0)
    chunk_coll["minecraft_chunk"] = 1

    # 2. Save chunk collection to external file if requested
    # Save mainfile to chunk destination
    if full_chunk_path:
        bpy.ops.wm.save_as_mainfile(filepath=full_chunk_path, copy=True)

    # 3. Clean up chunk objects from build scene
    for obj in list(chunk_coll.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

    bpy.data.collections.remove(chunk_coll, do_unlink=True)

    # 4. Purge orphans
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

    return {
        "ok": True,
        "name": chunk_name,
        "saved_path": full_chunk_path,
        "block_count": chunk_info.get("block_count", 0),
    }
