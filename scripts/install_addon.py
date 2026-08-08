"""
Run with: blender --background --python scripts/install_addon.py

Makes "the pipeline installs the add-on automatically" (Section 1) actually
true: copies addon/ into Blender's user addons folder (as module name
`strata_addon`, not the generic `addon`), enables it, and installs the
`strata` package itself into Blender's bundled Python -- addon-side code
(world_import/operators.py) imports strata.plugins.* directly, so it needs
`strata` importable from INSIDE Blender's Python, not just the system one
running the MCP server.

VERIFY: `bpy.utils.user_resource` and background-mode `addon_enable` /
`save_userpref` behavior can vary across Blender builds and platforms --
confirm this actually leaves the add-on enabled on a normal (non-background)
launch afterward; if it doesn't, enabling it once by hand in Preferences is
the fallback, not a blocker.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

import bpy

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE_ADDON_DIR = REPO_ROOT / "addon"
INSTALLED_MODULE_NAME = "strata_addon"


def install_strata_into_blender_python():
    try:
        subprocess.check_call([sys.executable, "-m", "ensurepip"])
    except subprocess.CalledProcessError:
        pass  # recent Blender builds usually ship pip already; ignore if this fails
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", str(REPO_ROOT)])


def install_addon_files() -> pathlib.Path:
    addons_dir = pathlib.Path(bpy.utils.user_resource("SCRIPTS", path="addons", create=True))
    target = addons_dir / INSTALLED_MODULE_NAME
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(SOURCE_ADDON_DIR, target)
    return target


def enable_addon():
    # refresh_script_paths() forces Blender to rescan its addons directories
    # after the manual shutil.copytree() above, without this the module cache
    # still points at the old (empty) state and addon_enable raises
    # ModuleNotFoundError: No module named 'strata_addon'.
    bpy.utils.refresh_script_paths()
    bpy.ops.preferences.addon_enable(module=INSTALLED_MODULE_NAME)
    bpy.ops.wm.save_userpref()



if __name__ == "__main__":
    print("Strata: installing strata into Blender's Python...")
    install_strata_into_blender_python()
    print("Strata: copying add-on files...")
    installed_at = install_addon_files()
    print(f"Strata: add-on installed at {installed_at}")
    print("Strata: enabling add-on...")
    enable_addon()
    print("Strata: done. Open Blender normally and look for the 'Strata' tab "
          "in the 3D viewport sidebar (press N if the sidebar is hidden).")
