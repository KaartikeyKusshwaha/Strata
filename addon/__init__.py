bl_info = {
    "name": "Strata",
    "author": "KK",
    "version": (0, 4, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Strata",
    "description": "Blender-side bridge for the Strata pipeline -- driven by strata.Pipeline, not used standalone",
    "category": "Object",
}

import bpy

from . import bridge_server
from . import chunk_workflow
from .world_import import operators as world_ops  # noqa: F401


class STRATA_OT_start_server(bpy.types.Operator):
    bl_idname = "strata.start_server"
    bl_label = "Start Strata Bridge"

    def execute(self, context):
        bridge_server.start()
        self.report({"INFO"}, f"Strata bridge listening on {bridge_server.DEFAULT_HOST}:{bridge_server.DEFAULT_PORT}")
        return {"FINISHED"}


class STRATA_OT_stop_server(bpy.types.Operator):
    bl_idname = "strata.stop_server"
    bl_label = "Stop Strata Bridge"

    def execute(self, context):
        bridge_server.stop()
        return {"FINISHED"}


ALL_CLASSES = (
    STRATA_OT_start_server,
    STRATA_OT_stop_server,
)


def register():
    chunk_workflow.register()
    for cls in ALL_CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    bridge_server.stop()
    for cls in reversed(ALL_CLASSES):
        bpy.utils.unregister_class(cls)
    chunk_workflow.unregister()
