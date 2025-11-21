"""
Path resolution utilities for PyInstaller compatibility.

This module provides centralized path resolution that works in both:
- Development mode (running from source .py files)
- PyInstaller frozen mode (running from compiled binary)

Uses modern pathlib for clean, cross-platform path handling.
"""

import sys
from pathlib import Path

from .log import logger


def get_base_path():
    """
    Get the base path for resource resolution.

    Returns the appropriate base directory depending on execution mode:
    - PyInstaller frozen: Returns sys._MEIPASS (temp extraction directory)
    - Normal Python: Returns the current working directory

    Returns:
        Path: Absolute path to base directory

    Example:
        >>> base = get_base_path()
        >>> # In frozen mode: Path('/tmp/_MEIxxxxxx/')
        >>> # In normal mode: Path('/home/user/workspace/autolib_v3/')
    """
    # pylint: disable=protected-access
    if hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
        logger.debug("Path resolution: PyInstaller frozen mode, base=%s", base)
        return base

    base = Path.cwd()
    logger.debug("Path resolution: Development mode, base=%s", base)
    return base


def get_resource_path(relative_path):
    """
    Get absolute path to a bundled resource from project root.

    Resolves paths correctly in both PyInstaller frozen and normal execution modes.
    Use this for any files bundled via PyInstaller's 'datas' parameter.

    Args:
        relative_path (str or Path): Path relative to project root
                                     (e.g., 'lib/services/static' or 'plugins/apis')

    Returns:
        str: Absolute path to the resource (as string for compatibility)

    Example:
        >>> # Get path to templates directory
        >>> templates_dir = get_resource_path('lib/services/web_server/templates')
        >>>
        >>> # Get path to plugins
        >>> plugins = get_resource_path('plugins/apis')
    """
    base = get_base_path()
    resource = base / relative_path

    logger.debug("get_resource_path(%s) -> %s", relative_path, resource)

    if not resource.exists():
        logger.warning("Resource path does not exist: %s", resource)
        logger.warning("  Base path: %s", base)
        logger.warning("  Relative path: %s", relative_path)
        # List what's actually in the base directory
        if base.exists():
            try:
                contents = list(base.iterdir())[:10]  # First 10 items
                logger.warning("  Base directory contains: %s", contents)
            except Exception as e:
                logger.warning("  Could not list base directory: %s", e)

    # Return as string for compatibility with libraries expecting string paths
    return str(resource)


def get_module_resource_path(module_file, relative_subpath):
    """
    Get resource path relative to a specific module's location.

    Simplified implementation: In both dev and frozen modes, __file__ points
    to the correct location. Just resolve relative to it.

    Args:
        module_file (str): The module's __file__ attribute
        relative_subpath (str or Path): Path relative to the module's directory
                                        (e.g., 'templates' or 'static')

    Returns:
        str: Absolute path to the resource (as string for compatibility)

    Example:
        >>> # In lib/services/web_server/templates_loader.py
        >>> template_dir = get_module_resource_path(__file__, 'templates')
        >>> # Development: '.../lib/services/web_server/templates'
        >>> # Frozen: '/tmp/_MEIxxxxxx/lib/services/web_server/templates'
    """
    # Convert module_file to Path and get its parent directory
    module_path = Path(module_file).resolve()
    module_dir = module_path.parent

    # Resolve the resource path
    resource = module_dir / relative_subpath

    logger.debug(
        "get_module_resource_path(%s, %s) -> %s (frozen=%s)",
        module_file,
        relative_subpath,
        resource,
        hasattr(sys, "_MEIPASS"),
    )

    if not resource.exists():
        logger.warning("Module resource path does not exist: %s", resource)
        logger.warning("  Module file: %s", module_file)
        logger.warning("  Module dir: %s", module_dir)
        logger.warning("  Subpath: %s", relative_subpath)
        # List what's in the module directory
        if module_dir.exists():
            try:
                contents = list(module_dir.iterdir())[:20]  # First 20 items
                logger.warning(
                    "  Module directory contains: %s", [p.name for p in contents]
                )
            except Exception as e:
                logger.warning("  Could not list module directory: %s", e)

    # Return as string for compatibility with libraries expecting string paths
    return str(resource)
