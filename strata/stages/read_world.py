"""Stage 1: Read World. Delegates to a `world_readers` plugin, streaming into SQLite WorldStore."""
from __future__ import annotations

from typing import Optional

from ..pipeline_state import PipelineState
from ..plugins.base import discover
from ..plugins.world_readers.anvil_reader import AnvilWorldReader
from ..world_store import WorldStore

BUILTIN = {"anvil": AnvilWorldReader}


class ReadWorldStage:
    def __init__(self, reader_name: str = "anvil"):
        self.reader_name = reader_name

    def run(self, state: PipelineState, world_path: str, y_min: Optional[int] = None, y_max: Optional[int] = None) -> PipelineState:
        readers = {**BUILTIN, **discover("world_readers")}
        reader_cls = readers.get(self.reader_name)
        if reader_cls is None:
            raise ValueError(f"No world_readers plugin named {self.reader_name!r}. Available: {sorted(readers)}")

        state.world_path = world_path
        if state.world_store is None:
            state.world_store = WorldStore()

        reader = reader_cls()
        block_stream = reader.read_blocks(world_path, y_min=y_min, y_max=y_max)
        inserted_count = state.world_store.insert_blocks(block_stream, batch_size=5000)
        state.stats["read_blocks_count"] = inserted_count
        return state
