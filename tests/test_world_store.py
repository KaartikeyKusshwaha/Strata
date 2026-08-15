"""Unit tests for WorldStore (Phase 1).

Tests SQLite database lifecycle, batch block insertion, 3D chunk key math,
SQL-backed culling, summary statistics, and PipelineState integration.
"""
from strata.pipeline_state import PipelineState
from strata.world_store import WorldStore


def test_world_store_creation_and_cleanup():
    ws = WorldStore(keep_work_store=False)
    db_path = ws.db_path
    assert db_path.exists()

    ws.close()
    assert not db_path.exists()


def test_batch_insert_and_3d_chunk_keys():
    with WorldStore(keep_work_store=False) as ws:
        test_blocks = [
            (0, 0, 0, "minecraft:stone"),
            (15, 15, 15, "minecraft:dirt"),
            (-1, 0, -1, "minecraft:grass_block"),
            (32, 64, 16, "minecraft:oak_log"),
        ]
        inserted = ws.insert_blocks(test_blocks)
        assert inserted == 4

        keys = ws.get_chunk_keys()
        # Expected 3D chunks:
        # (0, 0, 0) -> (0, 0, 0)
        # (15, 15, 15) -> (0, 0, 0)
        # (-1, 0, -1) -> (-1, 0, -1)
        # (32, 64, 16) -> (2, 4, 1)
        assert (0, 0, 0) in keys
        assert (-1, 0, -1) in keys
        assert (2, 4, 1) in keys

        c000_blocks = ws.get_blocks_for_chunk(0, 0, 0)
        assert len(c000_blocks) == 2


def test_cull_hidden_blocks_sql():
    with WorldStore(keep_work_store=False) as ws:
        # Create a solid 3x3x3 cube of stone blocks (27 blocks total)
        cube_blocks = []
        for x in range(3):
            for y in range(3):
                for z in range(3):
                    cube_blocks.append((x, y, z, "minecraft:stone"))

        ws.insert_blocks(cube_blocks)
        stats_before = ws.get_summary_stats()
        assert stats_before["total_blocks"] == 27
        assert stats_before["visible_blocks"] == 27

        # Center block (1, 1, 1) has 6 cardinal neighbors in the cube and should be culled
        culled = ws.cull_hidden_blocks()
        assert culled == 1

        stats_after = ws.get_summary_stats()
        assert stats_after["visible_blocks"] == 26

        # Verify center block is marked visible = 0
        c000 = ws.get_blocks_for_chunk(0, 0, 0, visible_only=True)
        assert len(c000) == 26
        pos_list = [(b["mc_x"], b["mc_y"], b["mc_z"]) for b in c000]
        assert (1, 1, 1) not in pos_list


def test_summary_stats():
    with WorldStore(keep_work_store=False) as ws:
        ws.insert_blocks([
            (0, 0, 0, "minecraft:stone"),
            (16, 0, 0, "minecraft:dirt"),
        ])
        stats = ws.get_summary_stats()
        assert stats["total_blocks"] == 2
        assert stats["visible_blocks"] == 2
        assert stats["visible_chunks"] == 2


def test_pipeline_state_integration():
    ws = WorldStore(keep_work_store=False)
    ws.insert_blocks([(5, 5, 5, "minecraft:stone")])

    state = PipelineState(world_store=ws)
    assert len(state.blocks) == 1
    assert state.blocks[0] == (5, 5, 5, "minecraft:stone")

    ws.close()
