"""Bridge command handlers for building prototype libraries inside Blender."""
import bpy
from .. import bridge_server
from .library_builder import build_prototype_mesh


@bridge_server.register_command("build_prototype_library")
def handle_build_prototype_library(templates: list):
    proto_coll = bpy.data.collections.get("Strata_Prototypes")
    if proto_coll is None:
        proto_coll = bpy.data.collections.new("Strata_Prototypes")
        bpy.context.scene.collection.children.link(proto_coll)
        proto_coll.hide_viewport = True
        proto_coll.hide_render = True

    created_names = []
    for tmpl in templates:
        obj = build_prototype_mesh(tmpl)
        if obj.name not in proto_coll.objects:
            proto_coll.objects.link(obj)
        created_names.append(obj.name)

    return {"created_prototypes": created_names}
