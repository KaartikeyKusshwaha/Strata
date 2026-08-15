"""Stage 4: Optimize. Hidden-block culling via SQL in WorldStore or in-memory fallback."""
from __future__ import annotations

from ..pipeline_state import PipelineState
from ..culling import cull_hidden_blocks


class OptimizeStage:
    def run(self, state: PipelineState) -> PipelineState:
        if state.world_store is not None:
            culled_count = state.world_store.cull_hidden_blocks()
            state.stats["culled_blocks_count"] = culled_count
        else:
            state.blocks = list(cull_hidden_blocks(state.blocks))
        return state
