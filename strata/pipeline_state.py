"""
Shared state threaded through the seven stages. Each stage's `run(state, ...)`
mutates and returns this same object -- see strata/stages/__init__.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple

if TYPE_CHECKING:
    from strata.world_store import WorldStore

Block = Tuple[int, int, int, str]                            # (x, y, z, block_id)
ChunkKey = Tuple[int, int]                                    # 2D (chunk_x, chunk_z)
ChunkKey3D = Tuple[int, int, int]                            # 3D (chunk_x, chunk_y, chunk_z)
ChunkContents = Dict[str, List[Tuple[int, int, int]]]         # block_id -> positions


@dataclass
class PipelineState:
    chunk_size: int = 16
    world_path: str | None = None
    library_blend_path: str | None = None
    block_map: Dict[str, str] = field(default_factory=dict)
    _blocks: List[Block] = field(default_factory=list)
    world_store: Optional[WorldStore] = None
    chunks: Dict[ChunkKey, ChunkContents] = field(default_factory=dict)
    unmapped_block_ids: Set[str] = field(default_factory=set)
    render_target: str = "eevee_cycles"
    stats: Dict[str, object] = field(default_factory=dict)
    environment_config: dict = field(default_factory=dict)

    @property
    def blocks(self) -> List[Block]:
        if self.world_store is not None:
            return self.world_store.to_legacy_blocks_list()
        return self._blocks

    @blocks.setter
    def blocks(self, value: List[Block]):
        self._blocks = value
