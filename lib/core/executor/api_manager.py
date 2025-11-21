"""
Base module for executor APIs with inspect-based auto-discovery.

This module provides automatic API discovery using the inspect module.
All public functions (not starting with _) in API modules are automatically
registered as APIs, with the module name serving as the category.

API DISCOVERY APPROACH:
=======================
This module uses UNIFIED FILESYSTEM DISCOVERY that works in both:
- Development mode: Running from source (.py files)
- PyInstaller frozen mode: Running from compiled binary

DISCOVERY FLOW:
===============
1. BUILD TIME (autotest.spec):
   - discover_hiddenimports() scans lib/core/executor/api/*.py
   - Creates list of modules to bundle
   - PyInstaller includes these modules in the binary

2. RUN TIME (this module):
   - _discover_modules_from_filesystem() scans the same directory
   - Uses pathlib.glob() to find .py/.pyc files
   - Works in both dev (source files) and frozen (extracted files in _MEIPASS)
   - Registers discovered modules as APIs

KEY INSIGHT: Both use filesystem scanning, guaranteed to stay in sync!

WHY HIDDENIMPORTS ARE STILL NEEDED:
===================================
Even though runtime discovery uses filesystem scanning, PyInstaller still
needs hiddenimports to know WHAT to bundle. Without hiddenimports:
- Modules won't be in the binary
- Filesystem scan finds nothing
- No APIs registered

With hiddenimports:
- Modules bundled in binary and extracted to _MEIPASS
- Filesystem scan finds them
- APIs registered successfully

See autotest.spec's discover_hiddenimports() for build-time discovery.
"""

import importlib
import importlib.util
import inspect
import sys
from pathlib import Path
from typing import Callable, Dict, Tuple

from lib.core.compiler.schema_loader import get_schema
from lib.core.executor.api.code_execution import _build_context
from lib.core.executor.api_params import ApiParams
from lib.services import get_base_path, logger
from lib.settings import PARAGRAPH_SEP

from . import api as api_package

# Global registry for APIs - populated by auto-discovery
_API_REGISTRY: Dict[str, Callable] = {}
_CATEGORY_REGISTRY: Dict[str, list] = {}

# Cache for API discovery results (for compile-time performance)
_DISCOVERY_CACHE: Tuple[Dict, Dict] = None
_BUILTIN_CATEGORY_PREFIX = "Built-In"

# pylint: disable=global-statement


def discover_apis(force_refresh=False):
    """
    Automatically discover all API modules and their public functions.

    Now scans BOTH:
    1. Built-in APIs from lib/core/executor/api/ package
    2. User-defined APIs from plugins/apis/ directory

    Args:
        force_refresh: If True, bypass cache and re-discover APIs

    Returns:
        Tuple of (api_registry, category_registry)

    Note:
        Results are cached after first discovery to improve compile-time
        performance. Use force_refresh=True to reload APIs after changes.
    """
    global _DISCOVERY_CACHE

    # Return cached result if available and not forcing refresh
    if not force_refresh and _DISCOVERY_CACHE is not None:
        return _DISCOVERY_CACHE

    # Clear existing registries
    _API_REGISTRY.clear()
    _CATEGORY_REGISTRY.clear()

    # Discover built-in APIs from package
    _discover_from_package(api_package, _BUILTIN_CATEGORY_PREFIX)

    # Discover user-defined APIs from directory
    base_path = get_base_path()
    plugins_dir = base_path / "plugins" / "apis"
    _discover_from_directory(str(plugins_dir), "User-Defined")

    # Cache the results
    _DISCOVERY_CACHE = (_API_REGISTRY.copy(), _CATEGORY_REGISTRY.copy())

    return _API_REGISTRY, _CATEGORY_REGISTRY


def _discover_modules_from_filesystem(package):
    """
    Discover module names by scanning package directory (UNIFIED approach).

    SIMPLIFIED DISCOVERY - WORKS IN BOTH MODES:
    ===========================================
    This function uses filesystem scanning with pathlib, which works in:
    - Development mode: Scans source .py files
    - PyInstaller frozen mode: Scans extracted files in _MEIPASS

    WHY THIS IS BETTER THAN DUAL-MODE APPROACH:
    ===========================================
    Previous implementation had 3 different discovery methods:
    1. pkgutil.iter_modules() for dev mode
    2. sys.modules scanning for frozen mode
    3. Filesystem glob in autotest.spec at build time

    New implementation: Single method works everywhere!
    - Same logic at build time (autotest.spec) and runtime
    - Simpler to understand and maintain
    - No sync issues between different discovery methods

    HOW IT WORKS:
    =============
    In both dev and frozen modes, package.__file__ points to __init__.py(c):
    - Dev: /path/to/lib/core/executor/api/__init__.py
    - Frozen: /tmp/_MEIxxxxxx/lib/core/executor/api/__init__.pyc

    We get the parent directory and glob for .py files. Even in frozen mode,
    PyInstaller extracts .py files (or .pyc) to _MEIPASS, so glob finds them!

    RELATIONSHIP WITH HIDDENIMPORTS:
    ================================
    This discovers module NAMES from the filesystem, but Python still needs
    to IMPORT them. PyInstaller won't bundle modules unless they're in
    autotest.spec's hiddenimports list.

    - hiddenimports: Tells PyInstaller WHAT to bundle
    - This function: Discovers WHAT got bundled (at runtime)

    Args:
        package: Python package object to scan

    Returns:
        list: Module names (file stems without .py extension)
    """
    try:
        # Get package directory from package.__file__
        package_file = Path(package.__file__)
        package_dir = package_file.parent

        logger.debug(
            "Discovering modules from filesystem: %s (frozen=%s)",
            package_dir,
            hasattr(sys, "_MEIPASS"),
        )

        # Scan for Python module files
        module_files = list(package_dir.glob("*.py*"))  # .py or .pyc
        module_names = [
            p.stem
            for p in module_files
            if p.stem != "__init__" and not p.stem.startswith("_")
        ]

        logger.debug("Discovered %d modules: %s", len(module_names), module_names)
        return module_names

    except Exception as e:
        logger.error("Failed to discover modules from filesystem: %s", e)
        return []


def _discover_from_package(package, category_prefix):
    """
    Discover and register APIs from an installed package.

    UNIFIED DISCOVERY APPROACH:
    ===========================
    Uses filesystem scanning (pathlib.glob) in BOTH dev and frozen modes.
    This is simpler and more reliable than the previous dual-mode approach.

    Previous approach (REMOVED):
    - Dev mode: pkgutil.iter_modules()
    - Frozen mode: sys.modules scanning
    - Problem: Two different methods that could get out of sync

    New approach (CURRENT):
    - Both modes: Filesystem scanning via pathlib
    - Works because PyInstaller extracts files to _MEIPASS
    - Same logic as autotest.spec's discover_hiddenimports()
    - Single source of truth: the filesystem

    RELATIONSHIP WITH autotest.spec:
    ================================
    - BUILD TIME (autotest.spec): Scans filesystem → creates hiddenimports list
    - RUN TIME (this function): Scans filesystem → discovers what got bundled
    - Both use pathlib.glob() → guaranteed to stay in sync!

    WHY HIDDENIMPORTS ARE STILL NEEDED:
    ===================================
    Even though we discover modules via filesystem, PyInstaller still needs
    hiddenimports to know WHAT to bundle. This function discovers WHAT got
    bundled after PyInstaller did its work.

    - Without hiddenimports: Modules not bundled → filesystem scan finds nothing
    - With hiddenimports: Modules bundled → filesystem scan finds them

    See discover_hiddenimports() in autotest.spec for build-time discovery.

    Args:
        package: Python package to scan
        category_prefix: Prefix for category names (e.g., "Built-In")
    """
    api_package_name = package.__name__

    # Discover modules via unified filesystem scanning
    module_names = _discover_modules_from_filesystem(package)

    if not module_names:
        logger.debug("No API modules discovered in package: %s", api_package_name)
        return

    # Import and register each discovered module
    for module_name in module_names:
        full_module_name = f"{api_package_name}.{module_name}"
        module = importlib.import_module(full_module_name)

        # Use module name as category
        category = f"{category_prefix} - {module_name.replace('_', ' ').title()}"

        # Register all public functions from this module
        _register_module_functions(module, category)


def _discover_from_directory(directory, category_prefix):
    """
    Discover APIs from a filesystem directory.

    Args:
        directory: Directory path to scan for .py files (string or Path)
        category_prefix: Prefix for category names
    """
    # Convert to Path for consistent handling
    dir_path = Path(directory)

    if not dir_path.exists():
        logger.info("User API directory not found: %s", dir_path)
        return

    # Add directory to path temporarily for imports
    abs_directory = str(dir_path.resolve())
    if abs_directory not in sys.path:
        sys.path.insert(0, abs_directory)

    try:
        # Find all .py files using pathlib
        for py_file in dir_path.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue

            # Import module dynamically
            module_name = py_file.stem  # File name without extension
            spec = importlib.util.spec_from_file_location(module_name, str(py_file))
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Use module name as category
                category = (
                    f"{category_prefix} - {module_name.replace('_', ' ').title()}"
                )

                # Register all public functions from this module
                _register_module_functions(module, category)

                logger.debug(
                    "Discovered user API module: %s from %s", module_name, py_file
                )

    finally:
        # Clean up sys.path
        if abs_directory in sys.path:
            sys.path.remove(abs_directory)


def is_builtin_category(api_obj):
    category = getattr(api_obj, "category", None)
    return category and category.startswith(_BUILTIN_CATEGORY_PREFIX)


def _register_module_functions(module, category):
    """
    Register all public functions from a module as APIs.

    Args:
        module: Python module to scan
        category: Category name for these APIs
    """
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        # Skip private functions
        if name.startswith("_"):
            continue

        # Special handling for 'else_' -> 'else' mapping
        api_endpoint = name.rstrip("_") if name.endswith("_") and name != "_" else name

        # Register the function
        _API_REGISTRY[api_endpoint] = obj
        # record category, as later ONLY non-built-in APIs needs context preparation
        setattr(obj, "category", category)

        # Register in category registry
        if category not in _CATEGORY_REGISTRY:
            _CATEGORY_REGISTRY[category] = []
        _CATEGORY_REGISTRY[category].append(api_endpoint)


def get_all_apis() -> Dict[str, Callable]:
    """
    Get all registered APIs.

    Returns:
        Dict mapping API names to functions
    """
    if not _API_REGISTRY:
        discover_apis()
    return _API_REGISTRY.copy()


def get_apis_by_category() -> Dict[str, list]:
    """
    Get APIs organized by category.

    Returns:
        Dict mapping category names to lists of API names
    """
    if not _CATEGORY_REGISTRY:
        discover_apis()
    return _CATEGORY_REGISTRY.copy()


def get_api_metadata(func: Callable) -> Dict:
    """
    Get metadata from an API function.

    Args:
        func: API function

    Returns:
        Dict with API metadata
    """
    return {
        "name": func.__name__,
        "doc": func.__doc__ or "No description available",
        "signature": str(inspect.signature(func)),
    }


class ApiMixin:
    """
    Mixin class providing API execution capabilities.

    Classes using this mixin get:
    - execute_api() method
    - has_api() method
    - Access to API registry
    """

    def execute_api(self, api_endpoint: str, parameters: Tuple):
        """
        Execute an API by name with automatic parameter adaptation.

        Args:
            api: API name
            parameters: Tuple of parameters (will be wrapped in ApiParams)

        Returns:
            API result

        Raises:
            AttributeError: If API not found
        """
        # Ensure APIs are discovered
        if not _API_REGISTRY:
            discover_apis()

        # Wrap parameters in ApiParams for modern APIs
        schema = get_schema(api_endpoint)
        if schema:
            params = ApiParams(parameters, schema)
            # Auto-validate parameters
            try:
                params.validate()
            except ValueError as e:
                raise ValueError(
                    f"Parameter validation failed for '{api_endpoint}': {e}"
                ) from e
        else:
            # No schema - wrap without validation
            params = ApiParams.from_tuple(parameters)

        # Get from registry
        if api_endpoint in _API_REGISTRY:
            func = _API_REGISTRY[api_endpoint]
            # Set execution context for API access
            executor = self.executor if hasattr(self, "executor") else self
            if not is_builtin_category(func):
                executor.context = _build_context(executor)

            return func(executor, params)

        raise AttributeError(f"API '{api_endpoint}' not found")

    def has_api(self, api_endpoint: str) -> bool:
        """
        Check if an API exists.

        Args:
            api: API name

        Returns:
            True if API exists
        """
        # Ensure APIs are discovered
        if not _API_REGISTRY:
            discover_apis()

        return api_endpoint in _API_REGISTRY


class ApiHandler(ApiMixin):
    """
    Handler for all executor APIs.

    This class uses inspect-based auto-discovery for automatic
    registration and categorization. No hardcoded API lists needed!

    APIs are discovered from the api/ package on first use.
    """

    def __init__(self, executor):
        """
        Initialize handler with executor reference.

        Args:
            executor: The Executor instance
        """
        self.executor = executor
        # Trigger discovery on initialization
        discover_apis()


class ApiRegistry:
    """
    Registry for executor operations with automatic categorization.

    NO hardcoded categories - all discovered from @operation decorators!
    """

    def __init__(self):
        """Initialize registry from decorated operations."""
        self._apis = get_all_apis()
        self._categories = get_apis_by_category()

    def get_api(self, name: str):
        """Get operation function by name."""
        return self._apis.get(name)

    def has_api(self, name: str) -> bool:
        """Check if operation exists."""
        return name in self._apis

    def list_apis(self, category: str = None):
        """List all operations, optionally filtered by category."""
        if category:
            return sorted(self._categories.get(category, []))
        return sorted(self._apis.keys())

    def list_categories(self):
        """List all operation categories (auto-discovered)."""
        return sorted(self._categories.keys())

    def get_api_info(self, name: str):
        """Get detailed information about an operation."""
        func = self._apis.get(name)
        if not func:
            return {}

        metadata = get_api_metadata(func)
        doc = metadata["doc"].strip() if metadata["doc"] else ""

        # Try to get schema information for enhanced help
        schema = get_schema(name)
        if schema:
            # Use schema for parameter info with CLI options
            params = []
            for param in schema.parameters:
                option_str = f" [{param.option}]" if param.option else ""
                type_str = param.type
                req_str = "required" if param.required else "optional"
                default_str = (
                    f" (default: {param.default})" if param.default is not None else ""
                )
                params.append(
                    f"{param.name}{option_str}: {param.description} ({type_str}, {req_str}){default_str}"
                )

            return {
                "name": metadata["name"],
                "description": schema.description
                or (doc.split("\n")[0] if doc else "No description available"),
                "full_doc": schema.get_help(),
                "parameters": params,
                "category": schema.category,
                "parse_mode": schema.parse_mode,
            }

        # Fallback to docstring parsing if no schema
        params = []
        if "Parameters:" in doc:
            param_section = doc.split("Parameters:")[1].split("\n\n")[0]
            params = [
                line.strip()
                for line in param_section.split("\n")
                if line.strip() and ":" in line
            ]

        return {
            "name": metadata["name"],
            "description": doc.split("\n")[0] if doc else "No description available",
            "full_doc": doc,
            "parameters": params,
        }

    def print_all_apis(self):
        """
        Print all operations grouped by category.

        NO HARDCODING - categories are auto-discovered from decorators!
        """
        print(f"{PARAGRAPH_SEP}\nAPI AVAILABLE TO USE\n{PARAGRAPH_SEP}\n")

        # Get all categories (auto-discovered!)
        categories = self.list_categories()

        if not categories:
            print("No API registered yet.")
            return

        # Print operations by category
        for category in categories:
            api_endpoints = self.list_apis(category)
            print(f"\n{category}:\n{'-' * len(category)}")

            for api_endpoint in api_endpoints:
                info = self.get_api_info(api_endpoint)
                desc = info["description"] if info else "No description"
                print(f"  • {api_endpoint:30s} - {desc}")

        total_apis = len(self._apis)
        total_cats = len(categories)
        print(f"\n\nTotal: {total_apis} APIs across {total_cats} categories")
        print("=" * 80)

    def get_statistics(self):
        """Get registry statistics."""
        return {
            "total_apis": len(self._apis),
            "total_categories": len(self._categories),
            "apis_by_category": {
                cat: len(ops) for cat, ops in self._categories.items()
            },
            "categories": list(self._categories.keys()),
        }
