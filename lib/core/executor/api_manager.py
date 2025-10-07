"""
Base module for executor APIs with inspect-based auto-discovery.

This module provides automatic API discovery using the inspect module.
All public functions (not starting with _) in API modules are automatically
registered as APIs, with the module name serving as the category.
"""

import importlib
import inspect
import pkgutil
from typing import Callable, Dict, Tuple

from lib.settings import PARAGRAPH_SEP

from . import api as api_package

# Global registry for APIs - populated by auto-discovery
_API_REGISTRY: Dict[str, Callable] = {}
_CATEGORY_REGISTRY: Dict[str, list] = {}


def discover_apis():
    """
    Automatically discover all API modules and their public functions.

    This function:
    1. Scans all modules in the 'api' package
    2. Finds all public functions (not starting with _)
    3. Registers them with module name as category
    4. Handles special name mappings (e.g., 'else' for 'else_')

    Returns:
        Tuple of (api_registry, category_registry)
    """
    # Clear existing registries
    _API_REGISTRY.clear()
    _CATEGORY_REGISTRY.clear()

    # Get the api package path
    api_path = api_package.__path__
    api_package_name = api_package.__name__

    # Iterate through all modules in the api package
    for _, module_name, ispkg in pkgutil.iter_modules(api_path):
        if ispkg:
            continue  # Skip sub-packages

        # Import the module
        full_module_name = f"{api_package_name}.{module_name}"
        module = importlib.import_module(full_module_name)

        # Use module name as category (e.g., 'device', 'command', 'buffer')
        category = module_name.replace("_", " ").title()

        # Find all public functions in the module
        for name, obj in inspect.getmembers(module, inspect.isfunction):
            # Skip private functions (starting with _)
            if name.startswith("_"):
                continue

            # Special handling for 'else_' -> 'else' mapping
            api_endpoint = (
                name.rstrip("_") if name.endswith("_") and name != "_" else name
            )

            # Register the function
            _API_REGISTRY[api_endpoint] = obj

            # Register in category registry
            if category not in _CATEGORY_REGISTRY:
                _CATEGORY_REGISTRY[category] = []
            _CATEGORY_REGISTRY[category].append(api_endpoint)

    return _API_REGISTRY, _CATEGORY_REGISTRY


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
        Execute an API by name.

        Args:
            api: API name
            parameters: Tuple of parameters

        Returns:
            API result

        Raises:
            AttributeError: If API not found
        """
        # Ensure APIs are discovered
        if not _API_REGISTRY:
            discover_apis()

        # Try to get from method (for backward compatibility with old _operation naming)
        method_name = f"_{api_endpoint}"
        if hasattr(self, method_name):
            func = getattr(self, method_name)
            return func(parameters)

        # Try to get from registry
        if api_endpoint in _API_REGISTRY:
            func = _API_REGISTRY[api_endpoint]
            return func(
                self.executor if hasattr(self, "executor") else self, parameters
            )

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

        method_name = f"_{api_endpoint}"
        return hasattr(self, method_name) or api_endpoint in _API_REGISTRY


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

        # Extract parameter info from docstring
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
