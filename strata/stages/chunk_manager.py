"""Stage 5: Chunk Manager. Buckets blocks into chunk groups via WorldStore or in-memory fallback."""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Tuple

from ..pipeline_state import ChunkContents, ChunkKey, PipelineState
from ..chunking import bucket_into_chunks


class ChunkManagerStage:
    def run(self, state: PipelineState) -> PipelineState:
        if state.world_store is not None:
            chunks: Dict[ChunkKey, ChunkContents] = defaultdict(lambda: defaultdict(list))
            chunk_keys = state.world_store.get_chunk_keys(visible_only=True)
            for cx, cy, cz in chunk_keys:
                key2d: ChunkKey = (cx, cz)
                block_rows = state.world_store.get_blocks_for_chunk(cx, cy, cz, visible_only=True)
                for row in block_rows:
                    block_id = row["block_id"]
                    pos = (row["mc_x"], row["mc_y"], row["mc_z"])
                    chunks[key2d][block_id].append(pos)
            state.chunks = dict(chunks)
        else:
            state.chunks = bucket_into_chunks(state.blocks, chunk_size=state.chunk_size)
        return state
