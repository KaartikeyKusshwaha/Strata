"""Blender-side builder for generating prototype meshes and materials from normalized template definitions."""
import bpy


def build_prototype_mesh(template_data: dict) -> bpy.types.Object:
    """Builds or returns a Blender prototype mesh object based on normalized template data."""
    name = template_data.get("prototype_name", "PrototypeBlock")

    if name in bpy.data.objects:
        return bpy.data.objects[name]

    # Create unit cube mesh (1x1x1 Z-up)
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)

    # 1x1x1 cube centered at (0.5, 0.5, 0.5) or (0,0,0)
    verts = [
        (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0), (1.0, 0.0, 1.0), (1.0, 1.0, 1.0), (0.0, 1.0, 1.0),
    ]
    faces = [
        (0, 1, 2, 3), # Bottom (-Z)
        (4, 7, 6, 5), # Top (+Z)
        (0, 4, 5, 1), # Front (-Y)
        (1, 5, 6, 2), # Right (+X)
        (2, 6, 7, 3), # Back (+Y)
        (3, 7, 4, 0), # Left (-X)
    ]

    mesh.from_pydata(verts, [], faces)
    mesh.update()

    return obj
