"""Environment builders: clouds, atmosphere, sky, sun.

All functions send commands over the Blender bridge (strata.blender_io).
No bpy imports -- these run from MCP server or any external process.
"""
from .cloud_builder import CloudConfig, build_clouds
from .atmosphere_builder import AtmosphereConfig, build_atmosphere
from .sky_builder import SkyConfig, build_sky
from .sun_builder import SunConfig, build_sun
from .water_builder import WaterConfig, build_water

__all__ = [
    "CloudConfig", "build_clouds",
    "AtmosphereConfig", "build_atmosphere",
    "SkyConfig", "build_sky",
    "SunConfig", "build_sun",
    "WaterConfig", "build_water",
]

