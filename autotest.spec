# -*- mode: python ; coding: utf-8 -*-


block_cipher = None

import os
import re
import subprocess
import time
from pathlib import Path


def tree_datas(source, dest_prefix):
    """
    Recursively collects all files from the source directory,
    preserving their relative paths under dest_prefix.
    Returns a list of tuples in the format (source_file, destination_folder).
    """
    data_files = []
    for root, dirs, files in os.walk(source):
        for file in files:
            file_src = os.path.join(root, file)
            # Calculate the destination folder: remove the source prefix and join with dest_prefix
            relative_path = os.path.relpath(root, source)
            dest_folder = os.path.join(dest_prefix, relative_path)
            data_files.append((file_src, dest_folder))
    return data_files


def bundle_tree(path):
    """
    Bundle entire directory tree with 1:1 source→dest mapping.

    Simplified helper for the common case where source path equals destination path.
    Eliminates repetitive tree_datas(path, path) calls.

    Args:
        path: Directory path to bundle (used as both source and destination)

    Returns:
        list: PyInstaller datas tuples

    Example:
        bundle_tree("lib/services/static")
        # Equivalent to: tree_datas("lib/services/static", "lib/services/static")
    """
    return tree_datas(path, path)


def get_linux_version():
    try:
        result = subprocess.run(
            ["cat", "/etc/lsb-release"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        print("*" * 70)
        print(result.stdout)
        print("*" * 70)
        if result.returncode == 0:
            matched = re.search(r"DISTRIB_RELEASE=([\d.]+)", result.stdout)
            if matched:
                version = matched.group(1)
                return version.replace(".", "")
    except Exception as e:
        print(f"Error detecting Linux version: {e}")
    return ""


def discover_hiddenimports():
    """
    Dynamically discover modules to include as hiddenimports.

    WHY HIDDENIMPORTS ARE NEEDED:
    ==============================
    PyInstaller's static analysis can miss modules that are:
    1. Imported dynamically using importlib.import_module()
    2. Imported conditionally (if/else blocks, try/except)
    3. Discovered at runtime via pkgutil or sys.modules scanning
    4. Imported via __import__() or exec()

    In this project, API modules are discovered at runtime via:
    - pkgutil.iter_modules() in development mode
    - sys.modules scanning in frozen mode (after this spec imports them)

    Without hiddenimports, these modules won't be bundled, causing:
    - ImportError when trying to load them
    - Missing API functionality (e.g., 'comment' API not found)
    - Template loading failures (missing path_utils)

    WHY DYNAMIC DISCOVERY:
    ======================
    Instead of manually maintaining a list like:
        hiddenimports=["lib.core.executor.api.buffer", "lib.core.executor.api.device", ...]

    We auto-discover by scanning the filesystem at BUILD TIME:
    - Add a new API module → automatically included
    - Remove an API module → automatically excluded
    - No manual updates needed
    - Single source of truth (the filesystem)

    Returns:
        list: Module paths for PyInstaller's hiddenimports
    """
    imports = []

    # Auto-discover all API modules from lib/core/executor/api/
    # These are loaded dynamically at runtime via api_manager.py's discover_apis()
    api_dir = Path("lib/core/executor/api")
    if api_dir.exists():
        api_modules = [
            f"lib.core.executor.api.{p.stem}"
            for p in api_dir.glob("*.py")
            if p.stem != "__init__"
        ]
        imports.extend(api_modules)
        print(f"Discovered {len(api_modules)} API modules: {api_modules}")

    # Critical service modules that are imported conditionally or dynamically
    critical_services = [
        # path_utils: Imported by templates_loader.py and template_env.py
        # Provides PyInstaller-aware path resolution for Jinja2 templates
        # Without this, template loading fails with "TemplateNotFound" errors
        "lib.services.path_utils",
    ]
    imports.extend(critical_services)
    print(f"Added {len(critical_services)} critical service modules")

    print(f"Total hiddenimports: {len(imports)}")
    return imports


a = Analysis(
    ["autotest.py"],
    pathex=["lib"],
    binaries=[],
    datas=[
        ("version", "."),
        ("lib/services/fos/static/pltrev.csv", "lib/services/fos/static/"),
        ("lib/core/compiler/static/cli_syntax.json", "lib/core/compiler/static/"),
    ]
    # Bundle directory trees with 1:1 source→dest mapping
    + bundle_tree("lib/services/web_server/templates")
    + bundle_tree("lib/core/device/ems/metadata")
    + bundle_tree("lib/services/static")
    + bundle_tree("plugins/apis")
    # Bundle built-in API modules as data files for filesystem discovery
    # This extracts .py files to _MEIPASS, enabling unified filesystem scanning
    # at runtime (same approach as plugins/apis user-defined APIs)
    + bundle_tree("lib/core/executor/api"),
    # Dynamic hiddenimports discovery - see discover_hiddenimports() function above
    # This auto-includes API modules and critical services without manual maintenance
    hiddenimports=discover_hiddenimports(),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)


linux_version = get_linux_version()
version_suffix = f"_{linux_version}" if linux_version else ""

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=f"autotest{version_suffix}",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    onefile=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
