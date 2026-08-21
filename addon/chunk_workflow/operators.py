# SPDX-License-Identifier: GPL-3.0-or-later
"""
operators.py
~~~~~~~~~~~~
All Blender operator classes for MC Chunk Workflow.
"""

from __future__ import annotations

import bpy

from . import chunk_utils, pick_utils

# Keymap storage for clean unregister
_ADDON_KEYMAPS: list[tuple] = []


# ---------------------------------------------------------------------------
# Viewport shading operators
# ---------------------------------------------------------------------------

class MC_OT_ViewportPerformanceMode(bpy.types.Operator):
    bl_idname = "mc.viewport_performance_mode"
    bl_label = "Performance Mode"
    bl_description = (
        "Show only the chunk containing the Steve rig, switch to Solid "
        "shading, and remove all other chunks from viewport evaluation"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            chunk_utils.show_rig_area(radius=0)
        except RuntimeError:
            pass  # Hero rig is optional
        viewports = chunk_utils.configure_viewports("SOLID")
        context.scene["mc_viewport_mode"] = "PERFORMANCE"
        self.report({"INFO"}, f"Performance mode enabled in {viewports} viewport(s)")
        return {"FINISHED"}



class MC_OT_ViewportLookdevMode(bpy.types.Operator):
    bl_idname = "mc.viewport_lookdev_mode"
    bl_label = "Lookdev Mode"
    bl_description = "Switch every 3D viewport to Material Preview for the currently visible chunks"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        chunk_utils.sync_chunk_layer_visibility()
        viewports = chunk_utils.configure_viewports("MATERIAL")
        context.scene["mc_viewport_mode"] = "LOOKDEV"
        self.report({"INFO"}, f"Lookdev mode enabled in {viewports} viewport(s)")
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Rig-relative chunk operators
# ---------------------------------------------------------------------------

class MC_OT_ShowRigChunk(bpy.types.Operator):
    bl_idname = "mc.show_rig_chunk"
    bl_label = "Rig Chunk"
    bl_description = "Show only the vertical chunk column that contains the Steve rig"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            result = chunk_utils.show_rig_area(radius=0)
        except RuntimeError as exc:
            self.report({"WARNING"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, f"Shown {result['shown']} chunk(s) at rig position")
        return {"FINISHED"}


class MC_OT_ShowRigNeighbors(bpy.types.Operator):
    bl_idname = "mc.show_rig_neighbors"
    bl_label = "Rig + Neighbors"
    bl_description = "Show the Steve rig's chunk plus one ring of neighboring horizontal chunks"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            result = chunk_utils.show_rig_area(radius=1)
        except RuntimeError as exc:
            self.report({"WARNING"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, f"Shown {result['shown']} chunk(s) around rig")
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Terrain selection lock
# ---------------------------------------------------------------------------

class MC_OT_LockTerrainSelection(bpy.types.Operator):
    bl_idname = "mc.lock_terrain_selection"
    bl_label = "Lock Terrain"
    bl_description = (
        "Prevent terrain blocks from intercepting selection of characters, "
        "props, cameras, and lights"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            chunk_utils.set_terrain_selection_locked(True)
        except RuntimeError as exc:
            self.report({"WARNING"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, "Terrain selection locked")
        return {"FINISHED"}


class MC_OT_UnlockTerrainSelection(bpy.types.Operator):
    bl_idname = "mc.unlock_terrain_selection"
    bl_label = "Unlock Blocks"
    bl_description = "Allow individual Minecraft blocks to be selected again"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            chunk_utils.set_terrain_selection_locked(False)
        except RuntimeError as exc:
            self.report({"WARNING"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, "Terrain blocks unlocked for individual editing")
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Hero rig selection
# ---------------------------------------------------------------------------

class MC_OT_SelectHeroRig(bpy.types.Operator):
    bl_idname = "mc.select_hero_rig"
    bl_label = "Select Steve Rig"
    bl_description = "Select the hero armature directly, even when terrain is locked"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            rig = chunk_utils.select_hero_rig(context)
        except RuntimeError as exc:
            self.report({"WARNING"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, f"Selected {rig.name}")
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Block-picking operators
# ---------------------------------------------------------------------------

class MC_OT_RayPickBlock(bpy.types.Operator):
    bl_idname = "mc.ray_pick_block"
    bl_label = "Pick Block by Ray"
    bl_description = (
        "Click a visible block using geometry ray-cast selection. "
        "Best for solid terrain; use Screen Box for dense tree blocks"
    )
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context, event):
        if context.area is None or context.area.type != "VIEW_3D":
            self.report({"WARNING"}, "Run this from a 3D Viewport.")
            return {"CANCELLED"}
        context.window_manager.modal_handler_add(self)
        self.report({"INFO"}, "Click a visible block — Right-click / Esc cancels.")
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type in {"RIGHTMOUSE", "ESC"}:
            return {"CANCELLED"}
        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            obj = pick_utils.pick_block_by_ray(
                context, event.mouse_region_x, event.mouse_region_y
            )
            if obj is None:
                self.report({"WARNING"}, "No block hit under cursor.")
                return {"CANCELLED"}
            pick_utils.select_block_object(context, obj, event)
            self.report({"INFO"}, f"Selected {obj.name} ({obj.get('block_id')})")
            return {"FINISHED"}
        return {"RUNNING_MODAL"}


class MC_OT_ScreenBoxPickBlock(bpy.types.Operator):
    bl_idname = "mc.screen_box_pick_block"
    bl_label = "Pick Block by Screen Box"
    bl_description = (
        "Click-select a visible block using projected bounding boxes. "
        "Ideal for dense tree leaves and overlapping geometry"
    )
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context, event):
        if context.area is None or context.area.type != "VIEW_3D":
            self.report({"WARNING"}, "Run this from a 3D Viewport.")
            return {"CANCELLED"}
        context.window_manager.modal_handler_add(self)
        self.report({"INFO"}, "Click a visible block — Right-click / Esc cancels.")
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type in {"RIGHTMOUSE", "ESC"}:
            return {"CANCELLED"}
        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            obj, detail = pick_utils.pick_block_by_screen_box(
                context, event.mouse_region_x, event.mouse_region_y
            )
            if obj is None:
                self.report({"WARNING"}, detail)
                return {"CANCELLED"}
            pick_utils.select_block_object(context, obj, event)
            self.report({"INFO"}, f"Selected {obj.name} ({obj.get('block_id')}). {detail}")
            return {"FINISHED"}
        return {"RUNNING_MODAL"}


class MC_OT_ClickSelectBlock(bpy.types.Operator):
    """Internal operator mapped to Left-click.
    Passes through to Blender's normal selection when no block is under the cursor."""
    bl_idname = "mc.click_select_block"
    bl_label = "MC Click Select Block"
    bl_description = (
        "Override viewport left-click only when the cursor is directly over "
        "a visible Minecraft block; otherwise Blender's normal selection applies"
    )
    bl_options = {"UNDO"}

    def invoke(self, context, event):
        if context.area is None or context.area.type != "VIEW_3D":
            return {"PASS_THROUGH"}
        if context.mode != "OBJECT":
            return {"PASS_THROUGH"}
        if event.type != "LEFTMOUSE":
            return {"PASS_THROUGH"}

        obj, detail = pick_utils.pick_block_by_screen_box(
            context, event.mouse_region_x, event.mouse_region_y
        )
        if obj is None:
            obj = pick_utils.pick_block_by_ray(
                context, event.mouse_region_x, event.mouse_region_y
            )
            detail = "scene ray"
        if obj is None:
            return {"PASS_THROUGH"}

        pick_utils.select_block_object(context, obj, event)
        context.area.tag_redraw()
        self.report({"INFO"}, f"Selected {obj.name} ({obj.get('block_id')}) via {detail}")
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Selected-chunk operators
# ---------------------------------------------------------------------------

class MC_OT_ShowSelectedChunk(bpy.types.Operator):
    bl_idname = "mc.show_selected_chunk"
    bl_label = "Selected Chunk"
    bl_description = "Show only the chunk that contains the currently selected block"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            result = chunk_utils.show_selected_chunk(0, 999, 0, context)
        except RuntimeError as exc:
            self.report({"WARNING"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, f"Shown {result['shown']} chunk; hidden {result['hidden']}")
        return {"FINISHED"}


class MC_OT_ShowSelectedNeighbors(bpy.types.Operator):
    bl_idname = "mc.show_selected_neighbors"
    bl_label = "Selected + Neighbors"
    bl_description = "Show the selected block's chunk plus an adjustable ring of neighbors"
    bl_options = {"REGISTER", "UNDO"}

    radius_x: bpy.props.IntProperty(name="X Radius", default=1, min=0, max=16)
    radius_z: bpy.props.IntProperty(name="Z Radius", default=1, min=0, max=16)

    def execute(self, context):
        try:
            result = chunk_utils.show_selected_chunk(
                self.radius_x, 999, self.radius_z, context
            )
        except RuntimeError as exc:
            self.report({"WARNING"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, f"Shown {result['shown']} chunks; hidden {result['hidden']}")
        return {"FINISHED"}


class MC_OT_ShowOriginRadius(bpy.types.Operator):
    bl_idname = "mc.show_origin_radius"
    bl_label = "Origin Radius"
    bl_description = "Show chunks within a radius of the world origin (0, 0, 0)"
    bl_options = {"REGISTER", "UNDO"}

    radius_x: bpy.props.IntProperty(name="X Radius", default=1, min=0, max=32)
    radius_z: bpy.props.IntProperty(name="Z Radius", default=1, min=0, max=32)

    def execute(self, context):
        result = chunk_utils.show_chunk_radius(0, 0, 0, self.radius_x, 999, self.radius_z)
        self.report({"INFO"}, f"Shown {result['shown']} chunks; hidden {result['hidden']}")
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Global show / hide / render operators
# ---------------------------------------------------------------------------

class MC_OT_ShowAllChunks(bpy.types.Operator):
    bl_idname = "mc.show_all_chunks"
    bl_label = "Show All Viewport"
    bl_description = "Make every chunk visible in the viewport (render already enabled)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        count = chunk_utils.show_all_chunks_viewport()
        chunk_utils.set_all_chunks_render(True)
        self.report({"INFO"}, f"Shown {count} chunks")
        return {"FINISHED"}


class MC_OT_HideAllChunks(bpy.types.Operator):
    bl_idname = "mc.hide_all_chunks"
    bl_label = "Hide All Viewport"
    bl_description = "Hide every chunk in the viewport while keeping render enabled"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        count = chunk_utils.hide_all_chunks_viewport()
        chunk_utils.set_all_chunks_render(True)
        self.report({"INFO"}, f"Hidden {count} chunks; render remains enabled")
        return {"FINISHED"}


class MC_OT_FinalRenderState(bpy.types.Operator):
    bl_idname = "mc.final_render_state"
    bl_label = "Final Render State"
    bl_description = "Enable render visibility for all chunks (viewport state unchanged)"
    bl_options = {"REGISTER", "UNDO"}

    show_viewport: bpy.props.BoolProperty(
        name="Also show in viewport", default=False
    )

    def execute(self, context):
        stats = chunk_utils.final_render_state(self.show_viewport)
        self.report({"INFO"}, f"Render enabled for {stats['chunks']} chunks")
        return {"FINISHED"}


class MC_OT_MakeSelectedMeshUnique(bpy.types.Operator):
    bl_idname = "mc.make_selected_mesh_unique"
    bl_label = "Make Selected Mesh Unique"
    bl_description = "Duplicate mesh data for explicitly selected static block objects"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from .paging import make_selected_mesh_unique
        count = make_selected_mesh_unique()
        self.report({"INFO"}, f"Duplicated mesh data for {count} selected static block object(s)")
        return {"FINISHED"}


class MC_OT_UnloadAllChunks(bpy.types.Operator):
    bl_idname = "mc.unload_all_chunks"
    bl_label = "Unload All Chunks"
    bl_description = "Unload all unpinned chunks from Blender memory"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        chunks_parent = chunk_utils.chunks_parent()
        if not chunks_parent:
            self.report({"WARNING"}, "No MC_Chunks_16x16x16 collection found")
            return {"CANCELLED"}

        from .paging import unload_chunk_collection
        count = 0
        for child in list(chunks_parent.children):
            if child.get("mc_kind") == "chunk":
                if unload_chunk_collection(child.name):
                    count += 1

        self.report({"INFO"}, f"Unloaded {count} chunk collection(s)")
        return {"FINISHED"}


class MC_OT_PinSelectedChunk(bpy.types.Operator):
    bl_idname = "mc.pin_selected_chunk"
    bl_label = "Pin Selected Chunk"
    bl_description = "Pin selected chunk collection to prevent LRU eviction"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        if not context.selected_objects:
            self.report({"WARNING"}, "No object selected")
            return {"CANCELLED"}

        obj = context.selected_objects[0]
        for coll in obj.users_collection:
            if coll.get("mc_kind") == "chunk":
                coll["strata_pinned"] = True
                self.report({"INFO"}, f"Pinned chunk {coll.name}")
                return {"FINISHED"}

        self.report({"WARNING"}, "Selected object does not belong to a chunk collection")
        return {"CANCELLED"}


class MC_OT_UnpinSelectedChunk(bpy.types.Operator):
    bl_idname = "mc.unpin_selected_chunk"
    bl_label = "Unpin Selected Chunk"
    bl_description = "Unpin selected chunk collection to allow LRU eviction"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        if not context.selected_objects:
            self.report({"WARNING"}, "No object selected")
            return {"CANCELLED"}

        obj = context.selected_objects[0]
        for coll in obj.users_collection:
            if coll.get("mc_kind") == "chunk":
                coll["strata_pinned"] = False
                self.report({"INFO"}, f"Unpinned chunk {coll.name}")
                return {"FINISHED"}

        self.report({"WARNING"}, "Selected object does not belong to a chunk collection")
        return {"CANCELLED"}


# ---------------------------------------------------------------------------
# Class registry
# ---------------------------------------------------------------------------

CLASSES = (
    MC_OT_ViewportPerformanceMode,
    MC_OT_ViewportLookdevMode,
    MC_OT_ShowRigChunk,
    MC_OT_ShowRigNeighbors,
    MC_OT_LockTerrainSelection,
    MC_OT_UnlockTerrainSelection,
    MC_OT_SelectHeroRig,
    MC_OT_ClickSelectBlock,
    MC_OT_ScreenBoxPickBlock,
    MC_OT_RayPickBlock,
    MC_OT_ShowSelectedChunk,
    MC_OT_ShowSelectedNeighbors,
    MC_OT_ShowOriginRadius,
    MC_OT_ShowAllChunks,
    MC_OT_HideAllChunks,
    MC_OT_FinalRenderState,
    MC_OT_PrintStats,
    MC_OT_MakeSelectedMeshUnique,
    MC_OT_UnloadAllChunks,
    MC_OT_PinSelectedChunk,
    MC_OT_UnpinSelectedChunk,
)


def _register_keymaps() -> None:
    wm = bpy.context.window_manager
    keyconfig = wm.keyconfigs.addon
    if not keyconfig:
        return
    km = keyconfig.keymaps.new(name="3D View", space_type="VIEW_3D")
    # Remove stale items first so hot-reloading the addon is safe.
    for item in list(km.keymap_items):
        if item.idname == "mc.click_select_block":
            km.keymap_items.remove(item)
    try:
        kmi = km.keymap_items.new(
            "mc.click_select_block", type="LEFTMOUSE", value="CLICK"
        )
    except TypeError:
        kmi = km.keymap_items.new(
            "mc.click_select_block", type="LEFTMOUSE", value="PRESS"
        )
    _ADDON_KEYMAPS.append((km, kmi))


def _unregister_keymaps() -> None:
    for km, kmi in _ADDON_KEYMAPS:
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            pass
    _ADDON_KEYMAPS.clear()


def register() -> None:
    _unregister_keymaps()
    for cls in CLASSES:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            pass


def unregister() -> None:
    _unregister_keymaps()
    for cls in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
