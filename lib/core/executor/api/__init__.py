"""
API package for executor operations.

This package contains all executor API modules organized by category.
Module names serve as category names automatically.

ZERO-MAINTENANCE DISCOVERY:
===========================
API modules are auto-discovered via filesystem scanning in BOTH modes:
- Development: Scans source .py files from project directory
- PyInstaller frozen: Scans .py files extracted to _MEIPASS

In autotest.spec, built-in APIs are bundled as BOTH:
1. hiddenimports: Auto-discovered, compiled into binary for Python imports
2. datas via bundle_tree(): Extracts .py files to _MEIPASS for discovery

This dual approach enables unified filesystem scanning at runtime.
No hardcoded module lists needed - just create a new .py file and it
will be automatically discovered at both build time and runtime.
"""
