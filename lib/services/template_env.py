"""
Jinja2 template environment for summary templates.

Simple, direct template loading that works in both development and PyInstaller modes.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

# Resolve static template directory relative to this module's location
# Works in both dev (__file__ points to source) and frozen (__file__ points to extracted location)
TEMPLATE_FILE_DIR = str(Path(__file__).parent / "static")

# Create Jinja2 environment for static templates
web_server_env = Environment(loader=FileSystemLoader(TEMPLATE_FILE_DIR))

# Pre-load summary template for performance
TEMPLATE_FILENAME = "summary.template"
LOADED_SUMMARY_TEMPLATE = web_server_env.get_template(TEMPLATE_FILENAME)

__all__ = ["LOADED_SUMMARY_TEMPLATE"]
