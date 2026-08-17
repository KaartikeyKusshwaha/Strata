"""Unit tests for library sources, texture stack precedence, and missing asset policy (Phase 3).
"""
import pytest
from strata import Pipeline
from strata.library_sources import (
    BuildEstimate,
    TextureSource,
    filter_non_block_assets,
    resolve_texture_stack,
)


def test_texture_stack_precedence_order(tmp_path):
    user_pack = tmp_path / "user_pack.zip"
    user_pack.write_bytes(b"user_pack_content")

    selected_pack = tmp_path / "selected_pack.zip"
    selected_pack.write_bytes(b"selected_pack_content")

    mc_jar = tmp_path / "1.21.1.jar"
    mc_jar.write_bytes(b"jar_content")

    stack = resolve_texture_stack(
        minecraft_jar=str(mc_jar),
        user_texture_packs=(str(user_pack),),
        selected_texture_packs=(str(selected_pack),),
    )

    assert len(stack) == 3
    assert stack[0].kind == "user_pack"
    assert stack[0].path == str(user_pack)
    assert len(stack[0].sha256) == 64

    assert stack[1].kind == "selected_pack"
    assert stack[1].path == str(selected_pack)

    assert stack[2].kind == "minecraft_jar"
    assert stack[2].path == str(mc_jar)


def test_missing_asset_policy_setting():
    p = Pipeline()
    assert p.state.missing_asset_policy == "generate"

    p.set_missing_asset_policy("error")
    assert p.state.missing_asset_policy == "error"

    with pytest.raises(ValueError):
        p.set_missing_asset_policy("invalid_policy")


def test_pipeline_texture_stack_chaining(tmp_path):
    jar_file = tmp_path / "minecraft.jar"
    jar_file.write_bytes(b"test_jar")

    p = Pipeline().use_texture_stack(minecraft_jar=str(jar_file))
    assert len(p.state.texture_sources) == 1
    assert p.state.texture_sources[0].kind == "minecraft_jar"


def test_build_own_library_mode():
    p = Pipeline().build_own_library("combined_v1")
    assert p.state.own_library_mode is True
    assert p.state.reference_profile_name == "combined_v1"

    # use_library should turn off own_library_mode
    p.use_library("custom.blend")
    assert p.state.own_library_mode is False
    assert p.state.library_blend_path == "custom.blend"


def test_filter_non_block_assets():
    candidates = [
        "Stone", "Oak_Planks", "A1_Steve_Rig",
        "Alex_Mesh", "Zombie_Head", "Diamond_Block"
    ]
    blocks, ignored = filter_non_block_assets(candidates)

    assert set(blocks) == {"Stone", "Oak_Planks", "Diamond_Block"}
    assert set(ignored) == {"A1_Steve_Rig", "Alex_Mesh", "Zombie_Head"}


def test_preflight_build_estimate():
    p = Pipeline()
    p.set_missing_asset_policy("generate")
    est = p.preflight_build()

    assert isinstance(est, BuildEstimate)
    assert est.missing_asset_policy == "generate"
    assert isinstance(est.missing_assets, list)
