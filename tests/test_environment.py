from strata.environment import (
    build_clouds, build_atmosphere, build_sky, build_sun, build_water,
    CloudConfig, AtmosphereConfig, SkyConfig, SunConfig, WaterConfig,
)
from strata.pipeline import Pipeline

def test_import_environment_modules():
    assert build_clouds is not None
    assert build_atmosphere is not None
    assert build_sky is not None
    assert build_sun is not None
    assert build_water is not None

def test_cloud_config_defaults():
    cfg = CloudConfig()
    assert cfg.height == 19.3
    assert cfg.noise_scale == 120.0

def test_atmosphere_config_defaults():
    cfg = AtmosphereConfig()
    assert cfg.dimensions == (9000, 9000, 2200)

def test_sky_config_defaults():
    cfg = SkyConfig()
    assert cfg.use_camera_sky is True

def test_sun_config_defaults():
    cfg = SunConfig()
    assert cfg.sun_mesh_scale == 35.7

def test_water_config_day_and_night_defaults():
    cfg_day = WaterConfig(mode="day")
    assert cfg_day.day_roughness == 0.19
    assert cfg_day.day_bump_strength == 0.055
    
    cfg_night = WaterConfig(mode="night")
    assert cfg_night.night_roughness == 0.22
    assert cfg_night.night_bump_strength == 0.080

def test_pipeline_has_build_environment():
    pipeline = Pipeline()
    assert hasattr(pipeline, "build_environment")

def test_pipeline_build_environment_is_chainable():
    pipeline = Pipeline()
    result = pipeline.build_environment(
        enable_clouds=False,
        enable_atmosphere=False,
        enable_sky=False,
        enable_sun=False,
        enable_water=False,
        water_mode="day",
        cloud_height=20.0,
        sun_angle_deg=60.0,
        hdri_path=""
    )
    assert result is pipeline

