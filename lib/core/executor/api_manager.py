"""
Base module for executor APIs with inspect-based auto-discovery.

This module provides automatic API discovery using the inspect module.
All public functions (not starting with _) in API modules are automatically
registered as APIs, with the module name serving as the category.
"""

import glob
import importlib
import importlib.util
import inspect
import os
import pkgutil
import sys
from typing import Callable, Dict, Tuple

from lib.core.compiler.schema_loader import get_schema
from lib.core.executor.api_params import ApiParams
from lib.services import logger
from lib.settings import PARAGRAPH_SEP

from . import api as api_package

# Global registry for APIs - populated by auto-discovery
_API_REGISTRY: Dict[str, Callable] = {}
_CATEGORY_REGISTRY: Dict[str, list] = {}

# Cache for API discovery results (for compile-time performance)
_DISCOVERY_CACHE: Tuple[Dict, Dict] = None


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
    _discover_from_package(api_package, "Built-In")

    # Discover user-defined APIs from directory
    _discover_from_directory("plugins/apis", "User-Defined")

    # Cache the results
    _DISCOVERY_CACHE = (_API_REGISTRY.copy(), _CATEGORY_REGISTRY.copy())

    return _API_REGISTRY, _CATEGORY_REGISTRY


def _discover_from_package(package, category_prefix):
    """
    Discover APIs from an installed package.

    Args:
        package: Python package to scan
        category_prefix: Prefix for category names
    """
    api_path = package.__path__
    api_package_name = package.__name__

    for _, module_name, ispkg in pkgutil.iter_modules(api_path):
        if ispkg:
            continue  # Skip sub-packages

        # Import the module
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
        directory: Directory path to scan for .py files
        category_prefix: Prefix for category names
    """
    if not os.path.exists(directory):
        logger.info("User API directory not found: %s", directory)
        return

    # Add directory to path temporarily for imports
    abs_directory = os.path.abspath(directory)
    if abs_directory not in sys.path:
        sys.path.insert(0, abs_directory)

    try:
        # Find all .py files
        for py_file in glob.glob(f"{directory}/**/*.py", recursive=True):
            if py_file.endswith("__init__.py"):
                continue

            # Import module dynamically
            module_name = os.path.splitext(os.path.basename(py_file))[0]
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Use module name as category
                category = (
                    f"{category_prefix} - {module_name.replace('_', ' ').title()}"
                )

                # Register all public functions from this module
                _register_module_functions(module, category)

                logger.info(
                    "Discovered user API module: %s from %s", module_name, py_file
                )

    finally:
        # Clean up sys.path
        if abs_directory in sys.path:
            sys.path.remove(abs_directory)


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
            return func(self.executor if hasattr(self, "executor") else self, params)

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
