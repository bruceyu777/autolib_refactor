"""
Jinja2 template loader configuration for web server.

CRITICAL FIX: Pre-load templates into memory to handle PyInstaller daemon forking.

When using PyInstaller's onefile mode with os.fork(), the child daemon process
may get a different _MEIPASS extraction directory. To avoid this, we pre-load
all templates into memory at module import time (in the parent process).
"""

from pathlib import Path

from jinja2 import DictLoader, Environment


def _load_templates_from_disk():
    """
    Load all template files from disk into memory.

    This is called once at module import time, before any daemon forking.
    Ensures templates are available even if _MEIPASS changes in child processes.

    Returns:
        dict: Mapping of template names to template content strings
    """
    templates = {}
    template_dir = Path(__file__).parent / "templates"

    if template_dir.exists():
        for template_file in template_dir.glob("*.template"):
            template_name = template_file.name
            template_content = template_file.read_text(encoding="utf-8")
            templates[template_name] = template_content

    return templates


# Pre-load all templates into memory at module import time
# This happens in the parent process before daemon forking
_TEMPLATES = _load_templates_from_disk()

# Use DictLoader instead of FileSystemLoader
# DictLoader keeps templates in memory, no disk access needed
web_server_template_env = Environment(loader=DictLoader(_TEMPLATES))
