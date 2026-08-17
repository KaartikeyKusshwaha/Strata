"""
The single entry point most callers (agents included) should use:

    from strata import Pipeline
    (
        Pipeline()
        .load_world("world/")
        .use_library("blocks.blend")
        .optimize()
        .build_chunks()
        .prepare_render()
        .save("scene.blend")
    )

Every method returns self, so calls chain. Each delegates to the matching
stage -- see strata/stages/ and docs/ARCHITECTURE.md.
"""
from __future__ import annotations

from typing import List, Literal, Optional, Tuple

from .pipeline_state import PipelineState
from .stages import (
    ReadWorldStage, ResolveAssetsStage, OptimizeStage, ChunkManagerStage,
    BuildGeometryStage, RenderPrepStage, AnimationPrepStage,
)
from .environment import (
    build_clouds, build_atmosphere, build_sky, build_sun, build_water,
    CloudConfig, AtmosphereConfig, SkyConfig, SunConfig, WaterConfig,
)
from .library_sources import BuildEstimate, resolve_texture_stack
from . import blender_io  # noqa: F401  (imported for save(); kept explicit for clarity)


class Pipeline:
    def __init__(self, chunk_size: int = 16, world_reader: str = "anvil", geometry_backend: str = "geometry_nodes"):
        self._state = PipelineState(chunk_size=chunk_size)
        self._world_reader_name = world_reader
        self._geometry_backend_name = geometry_backend

    def load_world(self, world_path: str, y_min: Optional[int] = None, y_max: Optional[int] = None) -> "Pipeline":
        self._state = ReadWorldStage(reader_name=self._world_reader_name).run(
            self._state, world_path=world_path, y_min=y_min, y_max=y_max
        )
        return self

    def use_library(self, library_blend_path: str) -> "Pipeline":
        self._state.library_blend_path = library_blend_path
        self._state.own_library_mode = False
        return self

    def use_texture_stack(
        self,
        minecraft_jar: str = "",
        user_texture_packs: Tuple[str, ...] = (),
        selected_texture_packs: Tuple[str, ...] = (),
    ) -> "Pipeline":
        """Configures texture precedence stack: user_packs (1st) -> selected_packs (2nd) -> minecraft_jar (3rd)."""
        self._state.texture_sources = resolve_texture_stack(
            minecraft_jar=minecraft_jar,
            user_texture_packs=user_texture_packs,
            selected_texture_packs=selected_texture_packs,
        )
        return self

    def set_missing_asset_policy(self, policy: Literal["generate", "error"]) -> "Pipeline":
        """Sets policy for unresolved assets: 'generate' (own-library fallback) or 'error' (stop build)."""
        if policy not in ("generate", "error"):
            raise ValueError(f"Invalid missing_asset_policy: {policy!r}. Must be 'generate' or 'error'.")
        self._state.missing_asset_policy = policy
        return self

    def build_own_library(self, reference_profile: str = "combined_v1") -> "Pipeline":
        """Enables own-library generator mode using committed reference profiles."""
        self._state.own_library_mode = True
        self._state.reference_profile_name = reference_profile
        return self

    def preflight_build(self, output_directory: str = "") -> BuildEstimate:
        """Returns preflight build estimates without building geometry."""
        stats = {}
        if self._state.world_store:
            stats = self._state.world_store.get_summary_stats()

        texture_sources_dicts = [
            {"kind": ts.kind, "path": ts.path, "sha256": ts.sha256}
            for ts in self._state.texture_sources
        ]

        return BuildEstimate(
            total_blocks=stats.get("total_blocks", len(self._state.blocks)),
            visible_blocks=stats.get("visible_blocks", len(self._state.blocks)),
            total_chunks=stats.get("visible_chunks", len(self._state.chunks)),
            missing_assets=sorted(list(self._state.unmapped_block_ids)),
            texture_sources=texture_sources_dicts,
            missing_asset_policy=self._state.missing_asset_policy,
        )

    def use_block_map(self, block_map_path: str) -> "Pipeline":
        self._state = ResolveAssetsStage().run(self._state, block_map_path=block_map_path)
        return self

    def optimize(self) -> "Pipeline":
        self._state = OptimizeStage().run(self._state)
        return self

    def build_chunks(self) -> "Pipeline":
        if self._state.missing_asset_policy == "error" and self._state.unmapped_block_ids:
            raise RuntimeError(
                f"Missing asset policy 'error' triggered: {len(self._state.unmapped_block_ids)} missing assets "
                f"({sorted(list(self._state.unmapped_block_ids))})"
            )
        self._state = ChunkManagerStage().run(self._state)
        self._state = BuildGeometryStage(backend_name=self._geometry_backend_name).run(self._state)
        return self

    def prepare_render(self, target: str = "eevee_cycles") -> "Pipeline":
        self._state = RenderPrepStage(target=target).run(self._state)
        return self

    def prepare_animation(self) -> "Pipeline":
        self._state = AnimationPrepStage().run(self._state)
        return self

    def build_environment(
        self,
        enable_clouds: bool = True,
        enable_atmosphere: bool = True,
        enable_sky: bool = True,
        enable_sun: bool = True,
        enable_water: bool = True,
        water_mode: str = "day",
        cloud_height: float = 19.3,
        sun_angle_deg: float = 45.0,
        hdri_path: str = "",
    ) -> "Pipeline":
        """Stage 6b: Build environment (clouds, atmosphere, sky, sun, water)."""
        import math
        results = {}
        if enable_clouds:
            cloud_cfg = CloudConfig(height=cloud_height)
            results["clouds"] = build_clouds(cloud_cfg)
        if enable_atmosphere:
            results["atmosphere"] = build_atmosphere(AtmosphereConfig())
        if enable_sky:
            sky_cfg = SkyConfig(hdri_path=hdri_path)
            results["sky"] = build_sky(sky_cfg)
        if enable_sun:
            # Convert angle to radians for lamp rotation
            angle_rad = math.radians(sun_angle_deg)
            sun_cfg = SunConfig(lamp_rotation=(angle_rad, 0.0, -2.601))
            results["sun"] = build_sun(sun_cfg)
        if enable_water:
            water_cfg = WaterConfig(mode=water_mode)
            results["water"] = build_water(water_cfg)
        self._state.environment_config = results
        return self

    def save(self, output_blend_path: str) -> "Pipeline":
        result = blender_io.call("save_scene", output_blend_path=output_blend_path)
        self._state.stats.update(result)
        return self

    @property
    def state(self) -> PipelineState:
        """Read-only-by-convention access to the working state, e.g.
        `pipeline.state.unmapped_block_ids` after `build_chunks()`."""
        return self._state
