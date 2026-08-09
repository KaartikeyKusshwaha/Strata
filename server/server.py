"""
Thin MCP wrapper around strata.Pipeline -- "two doors, one pipeline"
(docs/ARCHITECTURE.md). No pipeline logic lives here; every tool either
constructs a Pipeline and calls its public methods, or calls the bridge
directly for pure inspection commands. If a bug or a missing feature shows
up here, the fix almost always belongs in strata/, not in this file
(Core Architecture Rule / Reuse Before Reimplementation).
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from strata import Pipeline, blender_io

mcp = FastMCP("strata")


@mcp.tool()
def get_scene_status() -> dict:
    """Chunk/block counts and bridge connectivity for the active Blender file."""
    return blender_io.call("get_scene_status")


@mcp.tool()
def list_block_library(library_blend_path: str) -> dict:
    """Lists top-level object names in a block-library .blend, so the agent
    can reconcile them against Minecraft block ids before calling
    import_minecraft_world."""
    return blender_io.call("list_block_library", library_blend_path=library_blend_path)


@mcp.tool()
def import_minecraft_world(
    world_path: str,
    library_blend_path: str,
    output_blend_path: str,
    block_map_path: str = "",
    chunk_size: int = 16,
    y_min: int = -64,
    y_max: int = 319,
    render_target: str = "eevee_cycles",
) -> dict:
    """
    Reconstructs a real Minecraft save as a chunked, render-ready Blender
    scene: reads world_path, populates it using prototypes from
    library_blend_path (optionally reconciled through block_map_path),
    builds the chunk-toggle system, applies render_target, and saves to
    output_blend_path.

    Returns chunk/block counts and any block ids with no matching prototype
    (unmapped_block_ids) -- add those to the block map or the library
    .blend, then call this again. Never silently drops them (Error Handling).
    """
    pipeline = Pipeline(chunk_size=chunk_size)
    pipeline.load_world(world_path, y_min=y_min, y_max=y_max)
    pipeline.use_library(library_blend_path)
    if block_map_path:
        pipeline.use_block_map(block_map_path)
    pipeline.optimize()
    pipeline.build_chunks()
    pipeline.prepare_render(target=render_target)
    pipeline.save(output_blend_path)

    return {
        "unmapped_block_ids": sorted(pipeline.state.unmapped_block_ids),
        **pipeline.state.stats,
    }


@mcp.tool()
def generate_environment(
    enable_clouds: bool = True,
    enable_atmosphere: bool = True,
    enable_sky: bool = True,
    enable_sun: bool = True,
    enable_water: bool = True,
    water_mode: str = "day",
    cloud_height: float = 19.3,
    sun_angle_deg: float = 45.0,
    hdri_path: str = "",
) -> dict:
    """
    Generates A1-style blocky Minecraft clouds, atmospheric height fog,
    HDRI sky with camera-ray preservation, a visible sun mesh with
    independent directional lighting, and procedural water bodies (day/night modes).
    Call after import_minecraft_world to complete a production-ready scene.
    """
    pipeline = Pipeline()
    pipeline.build_environment(
        enable_clouds=enable_clouds,
        enable_atmosphere=enable_atmosphere,
        enable_sky=enable_sky,
        enable_sun=enable_sun,
        enable_water=enable_water,
        water_mode=water_mode,
        cloud_height=cloud_height,
        sun_angle_deg=sun_angle_deg,
        hdri_path=hdri_path,
    )
    return pipeline.state.environment_config



def main():
    mcp.run()


if __name__ == "__main__":
    main()
