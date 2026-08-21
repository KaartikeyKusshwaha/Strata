"""Unit tests for Java blockstate, model, texture parsing, and prototype acquisition (Phase 4).
"""
import pytest
from strata.minecraft_java import (
    element_to_blender_box,
    parse_blockstate_json,
    parse_model_json,
    resolve_texture_variable,
)
from strata.assets import acquire_prototype_template


def test_parse_blockstate_variants():
    json_str = """
    {
        "variants": {
            "": [
                { "model": "block/stone" },
                { "model": "block/stone_mirrored", "y": 180 }
            ]
        }
    }
    """
    models = parse_blockstate_json(json_str, mc_x=0, mc_y=0, mc_z=0)
    assert len(models) == 1
    assert models[0]["model"] == "block/stone"


def test_parse_blockstate_multipart():
    json_str = """
    {
        "multipart": [
            {
                "when": { "north": "true" },
                "apply": { "model": "block/fence_side", "uvlock": true }
            },
            {
                "apply": { "model": "block/fence_post" }
            }
        ]
    }
    """
    models = parse_blockstate_json(json_str, state_properties={"north": "true"})
    assert len(models) == 2
    assert models[0]["model"] == "block/fence_side"
    assert models[1]["model"] == "block/fence_post"


def test_parse_model_parent_chain():
    child_json = """
    {
        "parent": "block/cube",
        "textures": {
            "all": "block/stone"
        }
    }
    """
    parent_json = """
    {
        "textures": {
            "particle": "#all"
        },
        "elements": [
            {
                "from": [0, 0, 0],
                "to": [16, 16, 16]
            }
        ]
    }
    """
    def parent_resolver(ref):
        if ref == "block/cube":
            return parent_json
        return ""

    model = parse_model_json(child_json, parent_resolver=parent_resolver)
    assert model.textures["all"] == "block/stone"
    assert model.textures["particle"] == "#all"
    assert len(model.elements) == 1


def test_element_to_blender_box_conversion():
    element = {
        "from": [0, 0, 0],
        "to": [16, 16, 16],
        "faces": {"down": {"uv": [0, 0, 16, 16], "texture": "#all"}}
    }
    box = element_to_blender_box(element)
    assert box["min"] == (0.0, 0.0, 0.0)
    assert box["max"] == (1.0, 1.0, 1.0)


def test_resolve_texture_variable():
    texture_map = {
        "particle": "#all",
        "all": "block/stone",
    }
    assert resolve_texture_variable("#particle", texture_map) == "block/stone"
    assert resolve_texture_variable("#all", texture_map) == "block/stone"
    assert resolve_texture_variable("block/dirt", texture_map) == "block/dirt"


def test_acquire_prototype_template():
    # 1. User block map authority
    res1 = acquire_prototype_template("minecraft:stone", {"minecraft:stone": "MyCustomStone"})
    assert res1["source"] == "user_library"
    assert res1["prototype_name"] == "MyCustomStone"

    # 2. Reference profile lookup (Stone in combined_v1 profile)
    res2 = acquire_prototype_template("Stone", {})
    assert res2["source"] == "reference_profile"
    assert res2["prototype_name"] == "Stone"

    # 3. Generator fallback
    res3 = acquire_prototype_template("minecraft:unknown_custom_block", {}, own_library_mode=True)
    assert res3["source"] == "generated"
    assert res3["prototype_name"] == "UnknownCustomBlock"
