"""SQLite-backed world store for streaming, memory-bounded world processing.

Replaces in-memory block lists with a SQLite database stored in %LOCALAPPDATA%/Strata/work/
or system temp directories.
"""
import math
import os
import sqlite3
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

NON_OPAQUE = {"air", "cave_air", "void_air", "minecraft:air", "minecraft:cave_air", "minecraft:void_air"}


def get_default_work_dir() -> Path:
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        base = Path(local_app_data) / "Strata" / "work"
    else:
        base = Path(tempfile.gettempdir()) / "Strata" / "work"
    base.mkdir(parents=True, exist_ok=True)
    return base


class WorldStore:
    def __init__(
        self,
        run_id: Optional[str] = None,
        db_path: Optional[str] = None,
        keep_work_store: bool = False,
    ):
        self.run_id = run_id or uuid.uuid4().hex[:12]
        self.keep_work_store = keep_work_store

        if db_path:
            self.db_path = Path(db_path)
            self._is_temp = False
        else:
            work_dir = get_default_work_dir() / self.run_id
            work_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = work_dir / "world_store.db"
            self._is_temp = True

        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("PRAGMA synchronous = OFF")
        self.conn.execute("PRAGMA journal_mode = MEMORY")
        self._init_tables()

    def _init_tables(self):
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS blocks (
                    mc_x INTEGER NOT NULL,
                    mc_y INTEGER NOT NULL,
                    mc_z INTEGER NOT NULL,
                    block_id TEXT NOT NULL,
                    state_json TEXT,
                    block_entity_json TEXT,
                    chunk_x INTEGER NOT NULL,
                    chunk_y INTEGER NOT NULL,
                    chunk_z INTEGER NOT NULL,
                    visible INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (mc_x, mc_y, mc_z)
                )
            """
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_x INTEGER NOT NULL,
                    chunk_y INTEGER NOT NULL,
                    chunk_z INTEGER NOT NULL,
                    block_count INTEGER DEFAULT 0,
                    visible_block_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    PRIMARY KEY (chunk_x, chunk_y, chunk_z)
                )
            """
            )
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_blocks_chunk ON blocks(chunk_x, chunk_y, chunk_z)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_blocks_block_id ON blocks(block_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_blocks_visible ON blocks(visible)")

    def insert_blocks(self, block_tuples: Iterable[Tuple[Any, ...]], batch_size: int = 5000) -> int:
        """Inserts blocks in batches.

        Tuple formats supported:
        - (mc_x, mc_y, mc_z, block_id)
        - (mc_x, mc_y, mc_z, block_id, state_json)
        - (mc_x, mc_y, mc_z, block_id, state_json, block_entity_json)
        """
        records = []
        count = 0
        chunk_counts: Dict[Tuple[int, int, int], int] = {}

        for item in block_tuples:
            mc_x, mc_y, mc_z = int(item[0]), int(item[1]), int(item[2])
            block_id = str(item[3])
            state_json = str(item[4]) if len(item) > 4 and item[4] is not None else None
            block_entity_json = str(item[5]) if len(item) > 5 and item[5] is not None else None

            cx = math.floor(mc_x / 16)
            cy = math.floor(mc_y / 16)
            cz = math.floor(mc_z / 16)
            ckey = (cx, cy, cz)

            chunk_counts[ckey] = chunk_counts.get(ckey, 0) + 1
            records.append((mc_x, mc_y, mc_z, block_id, state_json, block_entity_json, cx, cy, cz, 1))
            count += 1

            if len(records) >= batch_size:
                self._flush_insert_batch(records)
                records = []

        if records:
            self._flush_insert_batch(records)

        # Update chunk counts
        self._update_chunk_stats(chunk_counts)
        return count

    def _flush_insert_batch(self, records: List[Tuple[Any, ...]]):
        with self.conn:
            self.conn.executemany(
                """
                INSERT OR REPLACE INTO blocks (
                    mc_x, mc_y, mc_z, block_id, state_json, block_entity_json,
                    chunk_x, chunk_y, chunk_z, visible
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                records,
            )

    def _update_chunk_stats(self, chunk_counts: Dict[Tuple[int, int, int], int]):
        with self.conn:
            for (cx, cy, cz), added in chunk_counts.items():
                self.conn.execute(
                    """
                    INSERT INTO chunks (chunk_x, chunk_y, chunk_z, block_count, visible_block_count, status)
                    VALUES (?, ?, ?, ?, ?, 'pending')
                    ON CONFLICT(chunk_x, chunk_y, chunk_z) DO UPDATE SET
                        block_count = block_count + excluded.block_count,
                        visible_block_count = visible_block_count + excluded.block_count
                """,
                    (cx, cy, cz, added, added),
                )

    def cull_hidden_blocks(self, non_opaque: Set[str] = NON_OPAQUE) -> int:
        """SQL-backed culling of blocks whose 6 cardinal neighbors are all opaque."""
        non_opaque_placeholders = ",".join("?" for _ in non_opaque)
        query = f"""
            UPDATE blocks
            SET visible = 0
            WHERE block_id NOT IN ({non_opaque_placeholders})
              AND EXISTS (SELECT 1 FROM blocks n WHERE n.mc_x = blocks.mc_x + 1 AND n.mc_y = blocks.mc_y AND n.mc_z = blocks.mc_z AND n.block_id NOT IN ({non_opaque_placeholders}))
              AND EXISTS (SELECT 1 FROM blocks n WHERE n.mc_x = blocks.mc_x - 1 AND n.mc_y = blocks.mc_y AND n.mc_z = blocks.mc_z AND n.block_id NOT IN ({non_opaque_placeholders}))
              AND EXISTS (SELECT 1 FROM blocks n WHERE n.mc_x = blocks.mc_x AND n.mc_y = blocks.mc_y + 1 AND n.mc_z = blocks.mc_z AND n.block_id NOT IN ({non_opaque_placeholders}))
              AND EXISTS (SELECT 1 FROM blocks n WHERE n.mc_x = blocks.mc_x AND n.mc_y = blocks.mc_y - 1 AND n.mc_z = blocks.mc_z AND n.block_id NOT IN ({non_opaque_placeholders}))
              AND EXISTS (SELECT 1 FROM blocks n WHERE n.mc_x = blocks.mc_x AND n.mc_y = blocks.mc_y AND n.mc_z = blocks.mc_z + 1 AND n.block_id NOT IN ({non_opaque_placeholders}))
              AND EXISTS (SELECT 1 FROM blocks n WHERE n.mc_x = blocks.mc_x AND n.mc_y = blocks.mc_y AND n.mc_z = blocks.mc_z - 1 AND n.block_id NOT IN ({non_opaque_placeholders}))
        """
        params = list(non_opaque) * 7
        with self.conn:
            cursor = self.conn.execute(query, params)
            culled_count = cursor.rowcount

        # Recalculate visible block counts per chunk
        with self.conn:
            self.conn.execute(
                """
                UPDATE chunks SET visible_block_count = (
                    SELECT COUNT(*) FROM blocks
                    WHERE blocks.chunk_x = chunks.chunk_x
                      AND blocks.chunk_y = chunks.chunk_y
                      AND blocks.chunk_z = chunks.chunk_z
                      AND blocks.visible = 1
                )
            """
            )
        return culled_count

    def get_chunk_keys(self, visible_only: bool = True) -> List[Tuple[int, int, int]]:
        query = "SELECT DISTINCT chunk_x, chunk_y, chunk_z FROM chunks"
        if visible_only:
            query += " WHERE visible_block_count > 0"
        query += " ORDER BY chunk_x, chunk_y, chunk_z"
        cursor = self.conn.execute(query)
        return [row for row in cursor.fetchall()]

    def get_blocks_for_chunk(self, cx: int, cy: int, cz: int, visible_only: bool = True) -> List[Dict[str, Any]]:
        query = "SELECT mc_x, mc_y, mc_z, block_id, state_json, block_entity_json FROM blocks WHERE chunk_x=? AND chunk_y=? AND chunk_z=?"
        if visible_only:
            query += " AND visible=1"
        cursor = self.conn.execute(query, (cx, cy, cz))
        results = []
        for row in cursor.fetchall():
            results.append({
                "mc_x": row[0],
                "mc_y": row[1],
                "mc_z": row[2],
                "block_id": row[3],
                "state_json": row[4],
                "block_entity_json": row[5],
            })
        return results

    def get_summary_stats(self) -> Dict[str, int]:
        cursor = self.conn.execute("SELECT COUNT(*), SUM(CASE WHEN visible=1 THEN 1 ELSE 0 END) FROM blocks")
        total_blocks, visible_blocks = cursor.fetchone()
        cursor = self.conn.execute("SELECT COUNT(*) FROM chunks WHERE visible_block_count > 0")
        visible_chunks = cursor.fetchone()[0]
        return {
            "total_blocks": total_blocks or 0,
            "visible_blocks": visible_blocks or 0,
            "visible_chunks": visible_chunks or 0,
        }

    def to_legacy_blocks_list(self, visible_only: bool = True) -> List[Tuple[int, int, int, str]]:
        """Compatibility helper for existing unit tests."""
        query = "SELECT mc_x, mc_y, mc_z, block_id FROM blocks"
        if visible_only:
            query += " WHERE visible=1"
        cursor = self.conn.execute(query)
        return cursor.fetchall()

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
        if self._is_temp and not self.keep_work_store and self.db_path.exists():
            try:
                self.db_path.unlink()
                if self.db_path.parent.exists() and not list(self.db_path.parent.iterdir()):
                    self.db_path.parent.rmdir()
            except OSError:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
