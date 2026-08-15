"""
Stage 3: Build Geometry. Reaches across the process boundary to Blender via blender_io.
Formats 3D A1 chunk names and coordinate payloads.
"""
from __future__ import annotations

from ..pipeline_state import PipelineState
from ..block_library import resolve_prototype_name
from ..chunking import format_a1_chunk_name
from .. import blender_io


class BuildGeometryStage:
    def __init__(self, backend_name: str = "geometry_nodes"):
        self.backend_name = backend_name

    def run(self, state: PipelineState) -> PipelineState:
        groups = []
        for key, block_groups in state.chunks.items():
            if len(key) == 3:
                cx, cy, cz = key[0], key[1], key[2]
            else:
                cx, cy, cz = key[0], 0, key[1]

            chunk_name = format_a1_chunk_name(cx, cy, cz)
            for block_id, positions in block_groups.items():
                groups.append({
                    "chunk_key": f"{cx}:{cy}:{cz}",
                    "chunk_name": chunk_name,
                    "chunk_x": cx,
                    "chunk_y": cy,
                    "chunk_z": cz,
                    "block_id": block_id,
                    "prototype_name": resolve_prototype_name(block_id, state.block_map),
                    "positions": positions,
                })

        result = blender_io.call(
            "build_geometry",
            library_blend_path=state.library_blend_path,
            groups=groups,
            backend_name=self.backend_name,
        )
        state.unmapped_block_ids = set(result.get("unmapped_block_ids", []))
        state.stats.update({k: v for k, v in result.items() if k != "unmapped_block_ids"})
        return state
