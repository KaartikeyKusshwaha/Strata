"""Unit tests for 3D A1 chunk identities (Phase 2).

Tests A1 chunk name formatting, parsing, roundtripping, coordinate system mapping,
and 3D chunk bucketing math.
"""
import pytest
from strata.chunking import (
    bucket_into_3d_chunks,
    format_a1_chunk_name,
    mc_to_blender_coords,
    parse_a1_chunk_name,
)


def test_format_a1_chunk_name_zero():
    assert format_a1_chunk_name(0, 0, 0) == "Chunk_xp000_yp000_zp000"


def test_format_a1_chunk_name_positive_and_negative():
    assert format_a1_chunk_name(1, -2, 3) == "Chunk_xp001_ym002_zp003"
    assert format_a1_chunk_name(-15, 0, 120) == "Chunk_xm015_yp000_zp120"
    assert format_a1_chunk_name(-100, -200, -300) == "Chunk_xm100_ym200_zm300"


def test_parse_a1_chunk_name():
    assert parse_a1_chunk_name("Chunk_xp000_yp000_zp000") == (0, 0, 0)
    assert parse_a1_chunk_name("Chunk_xp001_ym002_zp003") == (1, -2, 3)
    assert parse_a1_chunk_name("Chunk_xm015_yp000_zp120") == (-15, 0, 120)
    assert parse_a1_chunk_name("Chunk_xm100_ym200_zm300") == (-100, -200, -300)


def test_a1_chunk_name_roundtrip():
    test_coords = [
        (0, 0, 0),
        (1, -2, 3),
        (-5, -10, 15),
        (123, -456, 789),
        (-999, 999, 0),
    ]
    for cx, cy, cz in test_coords:
        formatted = format_a1_chunk_name(cx, cy, cz)
        parsed = parse_a1_chunk_name(formatted)
        assert parsed == (cx, cy, cz)


def test_parse_a1_chunk_name_invalid():
    with pytest.raises(ValueError):
        parse_a1_chunk_name("Chunk_invalid_name")

    with pytest.raises(ValueError):
        parse_a1_chunk_name("Chunk_1_2_3")


def test_mc_to_blender_coords():
    # Minecraft (X, Y, Z) -> Blender (X, Z, Y) where Y is vertical height in MC, Z is vertical in Blender
    assert mc_to_blender_coords(10, 64, -20) == (10, -20, 64)


def test_bucket_into_3d_chunks():
    test_blocks = [
        (0, 64, 0, "minecraft:stone"),
        (15, 79, 15, "minecraft:dirt"),
        (16, 80, 16, "minecraft:grass_block"),
        (-1, 64, -1, "minecraft:oak_log"),
    ]
    chunks = bucket_into_3d_chunks(test_blocks, chunk_size=16)

    # (0, 64, 0) -> cx=0, cy=4, cz=0
    # (15, 79, 15) -> cx=0, cy=4, cz=0
    # (16, 80, 16) -> cx=1, cy=5, cz=1
    # (-1, 64, -1) -> cx=-1, cy=4, cz=-1
    assert (0, 4, 0) in chunks
    assert len(chunks[(0, 4, 0)]["minecraft:stone"]) == 1
    assert len(chunks[(0, 4, 0)]["minecraft:dirt"]) == 1

    assert (1, 5, 1) in chunks
    assert (-1, 4, -1) in chunks
