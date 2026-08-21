"""Minecraft Java resource and model parsing subsystem.

No bpy imports required.
"""
from .blockstates import parse_blockstate_json
from .models import parse_model_json, ResolvedModel, element_to_blender_box
from .textures import resolve_texture_variable, extract_texture_image

__all__ = [
    "parse_blockstate_json",
    "parse_model_json",
    "ResolvedModel",
    "element_to_blender_box",
    "resolve_texture_variable",
    "extract_texture_image",
]
