"""Assets and prototype template manager package.

No bpy imports required.
"""
from .acquire import acquire_prototype_template
from .inventory import TemplateInventory
from .resource_stack import ResourcePackManager

__all__ = [
    "acquire_prototype_template",
    "TemplateInventory",
    "ResourcePackManager",
]
