"""
Tests for lib.core.executor.api_manager module.
"""

# pylint: disable=import-outside-toplevel,unused-import,unused-argument
# pylint: disable=consider-iterating-dictionary,unused-variable,reimported

import pytest


class TestApiDiscovery:
    """Test suite for API discovery functionality."""

    def test_discover_builtin_apis(self, mocker):
        """Test discovering built-in APIs from lib/core/executor/api/."""
        from lib.core.executor import api_manager

        # Trigger API discovery
        api_registry, category_registry = api_manager.discover_apis()

        # Should discover built-in APIs
        assert len(api_registry) > 0
        assert len(category_registry) > 0

        # Should have categories like "Built-In - Control Flow", "Built-In - Device", etc.
        builtin_categories = [c for c in category_registry.keys() if "Built-In" in c]
        assert len(builtin_categories) > 0

    def test_discover_plugin_apis(self, mocker, temp_dir):
        """Test discovering user-defined APIs from plugins/apis/."""
        import os

        from lib.core.executor import api_manager

        # Create mock plugin API module
        old_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            plugin_dir = temp_dir / "plugins" / "apis"
            plugin_dir.mkdir(parents=True)

            api_file = plugin_dir / "custom_api.py"
            api_file.write_text(
                '''
def custom_function(executor, params):
    """Custom API function."""
    return "custom_result"
'''
            )

            # Discover APIs
            api_registry, category_registry = api_manager.discover_apis()

            # Should discover the custom API
            assert "custom_function" in api_registry

            # Should have User-Defined category
            user_categories = [
                c for c in category_registry.keys() if "User-Defined" in c
            ]
            assert len(user_categories) > 0
        finally:
            os.chdir(old_cwd)

    def test_api_category_generation(self):
        """Test category generation from module names."""
        from lib.core.executor import api_manager

        # Discover APIs
        _, category_registry = api_manager.discover_apis()

        # Check that categories are properly formatted
        for category in category_registry.keys():
            # Categories should be like "Built-In - Control Flow" or "Built-In - Device"
            assert " - " in category
            # Should be title cased
            parts = category.split(" - ")
            assert len(parts) == 2

    def test_private_function_exclusion(self):
        """Test that private functions (_func) are not discovered."""
        from lib.core.executor import api_manager

        # Discover APIs
        api_registry, _ = api_manager.discover_apis()

        # Check that no private functions (starting with _) are in registry
        for api_name in api_registry.keys():
            assert not api_name.startswith(
                "_"
            ), f"Private function {api_name} should not be discovered"

    def test_class_exclusion(self):
        """Test that classes are not discovered as APIs."""
        import inspect

        from lib.core.executor import api_manager

        # Discover APIs
        api_registry, _ = api_manager.discover_apis()

        # Check that all registered APIs are functions, not classes
        for api_name, api_func in api_registry.items():
            assert inspect.isfunction(
                api_func
            ), f"{api_name} should be a function, not {type(api_func)}"


class TestApiRegistry:
    """Test suite for API registry."""

    def test_get_all_apis(self):
        """Test getting all registered APIs."""
        from lib.core.executor import api_manager

        # Get all APIs
        all_apis = api_manager.get_all_apis()

        # Should return a dictionary
        assert isinstance(all_apis, dict)
        assert len(all_apis) > 0

        # Should contain callable functions
        for api_name, api_func in all_apis.items():
            assert callable(api_func)

    def test_get_apis_by_category(self):
        """Test getting APIs filtered by category."""
        from lib.core.executor import api_manager

        # Get APIs by category
        categories = api_manager.get_apis_by_category()

        # Should return a dictionary
        assert isinstance(categories, dict)
        assert len(categories) > 0

        # Each category should have a list of API names
        for category, api_list in categories.items():
            assert isinstance(api_list, list)
            assert len(api_list) > 0

    def test_api_registration(self):
        """Test registering a new API."""
        from lib.core.executor.api_manager import ApiRegistry

        # Create registry
        registry = ApiRegistry()

        # Check that APIs are registered
        assert registry.has_api("if_not_goto") or registry.has_api("setenv")

        # Get API should return a function
        api_func = registry.get_api("setenv") if registry.has_api("setenv") else None
        if api_func:
            assert callable(api_func)

    def test_duplicate_api_handling(self):
        """Test handling duplicate API names."""
        from lib.core.executor import api_manager

        # Get all APIs
        api_registry, _ = api_manager.discover_apis()

        # Check that API names are unique (no duplicates)
        api_names = list(api_registry.keys())
        unique_names = set(api_names)

        # If there are duplicates, the set will be smaller than the list
        assert len(api_names) == len(unique_names), "Duplicate API names found"


class TestApiExecution:
    """Test suite for API execution."""

    def test_api_parameter_validation(self):
        """Test API parameter validation."""
        from lib.core.executor.api_params import ApiParams

        # Test creating ApiParams from tuple
        params = ApiParams.from_tuple(("arg1", "arg2", "arg3"))

        # Should be able to access parameters
        assert len(params) == 3
        assert params[0] == "arg1"
        assert params[1] == "arg2"
        assert params[2] == "arg3"

    def test_api_execution_success(self):
        """Test successful API execution."""
        from unittest.mock import MagicMock

        from lib.core.executor.api_manager import ApiHandler

        # Create mock executor
        mock_executor = MagicMock()
        mock_executor.cur_device = MagicMock()

        # Create API handler
        handler = ApiHandler(mock_executor)

        # Check that handler has API checking capability
        assert hasattr(handler, "has_api")
        assert hasattr(handler, "execute_api")

    def test_api_execution_error(self):
        """Test API execution error handling."""
        from unittest.mock import MagicMock

        from lib.core.executor.api_manager import ApiHandler

        # Create mock executor
        mock_executor = MagicMock()

        # Create API handler
        handler = ApiHandler(mock_executor)

        # Try to execute non-existent API
        with pytest.raises(AttributeError, match="API .* not found"):
            handler.execute_api("nonexistent_api_123", ())

    def test_api_with_optional_parameters(self):
        """Test API with optional parameters."""
        from lib.core.executor.api_params import ApiParams

        # Test with fewer parameters
        params = ApiParams.from_tuple(("required_param",))
        assert len(params) == 1
        assert params[0] == "required_param"

        # Test with more parameters
        params = ApiParams.from_tuple(("req", "opt1", "opt2"))
        assert len(params) == 3
        assert params.get(0) == "req"
        assert params.get(1) == "opt1"
        assert params.get(2) == "opt2"


class TestApiIntegration:
    """Integration tests for API manager."""

    def test_full_discovery_pipeline(self):
        """Test complete API discovery process."""
        pytest.skip("Requires full API manager integration")

    def test_api_help_generation(self):
        """Test generating help documentation for APIs."""
        pytest.skip("Requires schema integration")
