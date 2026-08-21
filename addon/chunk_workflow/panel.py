# SPDX-License-Identifier: GPL-3.0-or-later
"""
panel.py
~~~~~~~~
N-sidebar panel for MC Chunk Workflow.
"""

from __future__ import annotations

import bpy

from . import chunk_utils


class VIEW3D_PT_MCChunkWorkflow(bpy.types.Panel):
    bl_label = "MC Chunk Workflow"
    bl_idname = "VIEW3D_PT_mc_chunk_workflow"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MC World"

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        stats = chunk_utils.world_stats()

        # ------------------------------------------------------------------
        # Header stats
        # ------------------------------------------------------------------
        col = layout.column(align=True)
        col.label(
            text=f"Chunks: {stats['chunks']}  |  Visible: {stats['visible_chunks']}"
        )
        col.label(text=f"Visible objects: {stats['visible_objects']:,}")

        layout.separator()

        # ------------------------------------------------------------------
        # Viewport Performance
        # ------------------------------------------------------------------
        layout.label(text="Viewport Performance")

        row = layout.row(align=True)
        row.operator("mc.viewport_performance_mode", icon="SHADING_SOLID")
        row.operator("mc.viewport_lookdev_mode", icon="MATERIAL")

        # Terrain lock state indicator + toggle buttons
        locked = chunk_utils.terrain_selection_locked()
        layout.label(text=f"Terrain selection: {'LOCKED' if locked else 'UNLOCKED'}")
        row = layout.row(align=True)
        row.operator("mc.lock_terrain_selection", depress=locked, icon="LOCKED")
        row.operator("mc.unlock_terrain_selection", depress=not locked, icon="UNLOCKED")

        layout.separator()

        # ------------------------------------------------------------------
        # Block Edit Tools
        # ------------------------------------------------------------------
        layout.label(text="Block Edit Tools")
        layout.operator("mc.show_selected_chunk", icon="RESTRICT_VIEW_OFF")
        layout.operator("mc.show_selected_neighbors", icon="OUTLINER_COLLECTION")
        layout.operator("mc.make_selected_mesh_unique", icon="DUPLICATE")

        layout.separator()

        # ------------------------------------------------------------------
        # Chunk Streaming & Paging
        # ------------------------------------------------------------------
        layout.label(text="Chunk Streaming & Paging")
        row = layout.row(align=True)
        row.operator("mc.pin_selected_chunk", icon="PINNED")
        row.operator("mc.unpin_selected_chunk", icon="UNPINNED")
        layout.operator("mc.unload_all_chunks", icon="TRASH")

        layout.operator("mc.hide_all_chunks", icon="HIDE_ON")
        layout.operator("mc.show_all_chunks", icon="HIDE_OFF")
        layout.operator("mc.final_render_state", icon="RENDER_STILL")
        layout.operator("mc.print_world_stats", icon="INFO")



CLASSES = (VIEW3D_PT_MCChunkWorkflow,)


def register() -> None:
    for cls in CLASSES:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            pass


def unregister() -> None:
    for cls in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
