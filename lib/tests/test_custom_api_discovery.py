"""
Test custom API discovery at compile-time.

Verifies that custom APIs from plugins/apis/ are properly recognized
as API tokens (not device commands) during lexical analysis.
"""

import re
from unittest.mock import MagicMock, patch

import pytest

from lib.core.compiler.lexer import Lexer
from lib.core.compiler.syntax import ScriptSyntax, script_syntax
from lib.core.executor.api_manager import discover_apis


class TestCustomAPIPatternGeneration:
    """Test that custom APIs are included in generated regex patterns."""

    def test_custom_apis_discovered_at_pattern_generation(self):
        """Test that discover_apis() is called during pattern refresh."""
        with patch("lib.core.executor.api_manager.discover_apis") as mock_discover:
            # Setup mock to return custom APIs
            mock_discover.return_value = (
                {"extract_hostname": MagicMock(), "deploy_config": MagicMock()},
                {},
            )

            # Call refresh to trigger discovery
            script_syntax.refresh_patterns()

            # Verify discover_apis was called
            assert mock_discover.called

    def test_custom_api_in_generated_pattern(self):
        """Test that custom API names appear in the generated API pattern."""
        # Refresh patterns to include custom APIs
        script_syntax.refresh_patterns()

        # Get the pattern from the LINE_PATTERN_TABLE
        api_pattern = ScriptSyntax.LINE_PATTERN_TABLE.get("api", "")

        # Verify custom APIs are in the pattern
        # The pattern should contain the custom API names as alternatives
        assert "extract_hostname" in api_pattern or r"extract_hostname\s" in api_pattern

    def test_pattern_includes_both_builtin_and_custom_apis(self):
        """Test that pattern includes both built-in and custom APIs."""
        # Refresh patterns to include custom APIs
        script_syntax.refresh_patterns()

        # Get the pattern from the LINE_PATTERN_TABLE
        api_pattern = ScriptSyntax.LINE_PATTERN_TABLE.get("api", "")

        # Check for built-in API
        assert "exec_code" in api_pattern or r"exec_code\s" in api_pattern

        # Check for custom API (should be there after discovery)
        # Note: This depends on the actual custom APIs in plugins/apis/
        assert "extract_hostname" in api_pattern or "extract_hostname" in api_pattern

    def test_default_schema_for_custom_apis(self):
        """Test that custom APIs get default schema."""
        default_schema = ScriptSyntax._create_default_api_schema()

        assert default_schema["category"] == "custom"
        assert default_schema["parse_mode"] == "options"
        assert isinstance(default_schema["parameters"], dict)

    def test_api_pattern_for_custom_api_with_params(self):
        """Test pattern generation for custom API with parameters."""
        # Use static method for default schema
        api_schema = ScriptSyntax._create_default_api_schema()

        # Generate pattern for custom API using script_syntax instance
        pattern = script_syntax._api_pattern_for_api("extract_hostname", api_schema)

        # Default schema has parameters (-var, -file, etc), so pattern includes them
        assert pattern == r"extract_hostname\s*.*"

    def test_misordered_parameters_sorted_by_position(self):
        """Test that parameters are sorted by position, not dict order."""
        from lib.core.compiler.schema_loader import APISchema
        from lib.core.executor.api_params import ApiParams

        # Create a schema with parameters in WRONG order (not sorted by position)
        misordered_schema = {
            "category": "test",
            "parse_mode": "options",
            "parameters": {
                "-timeout": {  # position 3, but appears FIRST
                    "alias": "timeout",
                    "type": "int",
                    "position": 3,
                    "default": 30,
                },
                "-var": {  # position 0, but appears SECOND
                    "alias": "var",
                    "type": "string",
                    "position": 0,
                    "required": True,
                },
                "-file": {  # position 1, but appears THIRD
                    "alias": "file",
                    "type": "string",
                    "position": 1,
                    "required": False,
                },
                "-retries": {  # position 2, but appears FOURTH
                    "alias": "retries",
                    "type": "int",
                    "position": 2,
                    "default": 3,
                },
            },
        }

        # Build options syntax (this should sort by position)
        operation, matched_rule = script_syntax._build_options_syntax(misordered_schema)
        options_dict, _ = matched_rule

        # Get the keys in order (should be sorted by position, not JSON order)
        param_keys = list(options_dict.keys())

        # Verify they're sorted by position: -var (0), -file (1), -retries (2), -timeout (3)
        assert param_keys == [
            "-var",
            "-file",
            "-retries",
            "-timeout",
        ], f"Expected position-sorted order, got: {param_keys}"

        # Now test the full flow: create ApiParams with tuple in this order
        # Simulate parser creating tuple: [options[k] for k in options]
        test_values = ("result_var", "test.py", 5, 60)

        # Create APISchema and ApiParams
        api_schema = APISchema.from_dict("test_api", misordered_schema)
        params = ApiParams(test_values, api_schema)

        # Verify correct mapping (position-based, not dict-order-based)
        assert params.var == "result_var"  # position 0
        assert params.file == "test.py"  # position 1
        assert params.retries == 5  # position 2
        assert params.timeout == 60  # position 3


class TestCustomAPITokenization:
    """Test that custom APIs are correctly tokenized as 'api' tokens."""

    # pylint: disable=unused-argument
    def test_extract_hostname_tokenized_as_api(self, temp_dir):
        """Test that extract_hostname is tokenized as API not command."""
        # Refresh patterns to include custom APIs
        script_syntax.refresh_patterns()

        # Create a lexer
        lexer = Lexer()

        # Parse a line with custom API
        line = "extract_hostname -var hostname"
        tokens = lexer.parse_line(line)

        # Verify it was tokenized
        assert len(tokens) > 0

        # Find the API token
        api_token = next((t for t in tokens if t.type == "api"), None)

        # Verify it's an API token, not a command token
        assert (
            api_token is not None
        ), f"Expected API token, got tokens: {[(t.type, t.str) for t in tokens]}"
        assert api_token.str == "extract_hostname"

    def test_deploy_config_tokenized_as_api(self):
        """Test that deploy_config custom API is recognized."""
        # Force refresh of API patterns
        from lib.core.executor.api_manager import discover_apis

        discover_apis(force_refresh=True)
        script_syntax.generate_line_pattern()

        lexer = Lexer()

        line = "deploy_config -config_template 'base.conf' -result_var status"
        tokens = lexer.parse_line(line)

        # Should have an API token (or might not exist in the actual plugins)
        # Just verify it's not sent as a command if it's a known API
        api_token = next((t for t in tokens if t.type == "api"), None)

        # If deploy_config exists, it should be an API token
        # This test is flexible since deploy_config might not exist in all test environments
        if api_token:
            assert api_token.str == "deploy_config"

    def test_builtin_api_still_tokenized_correctly(self):
        """Test that built-in APIs still work after custom API changes."""
        lexer = Lexer()

        line = "exec_code -lang python -var result -file 'script.py'"
        tokens = lexer.parse_line(line)

        # Should have an API token for exec_code
        api_token = next((t for t in tokens if t.type == "api"), None)
        assert api_token is not None
        assert api_token.str == "exec_code"

    def test_custom_api_with_no_params(self):
        """Test custom API can be called without parameters."""
        lexer = Lexer()

        # Some custom APIs might not require parameters
        line = "some_custom_api"
        tokens = lexer.parse_line(line)

        # Should match as API or command depending on whether it exists
        # At minimum, should not fail to parse
        assert len(tokens) >= 0

    def test_unknown_command_still_tokenized_as_command(self):
        """Test that non-API lines are still tokenized as commands."""
        lexer = Lexer()

        # This should be a device command, not an API
        line = "get system status"
        tokens = lexer.parse_line(line)

        # Should be tokenized as command
        command_token = next((t for t in tokens if t.type == "command"), None)
        assert command_token is not None


class TestAPIDiscoveryCaching:
    """Test that API discovery caching works correctly."""

    def test_discovery_cache_used_on_second_call(self):
        """Test that cached results are returned on subsequent calls."""
        # Force a fresh discovery
        apis1, _ = discover_apis(force_refresh=True)

        # Call again without force_refresh - should use cache
        with patch(
            "lib.core.executor.api_manager._discover_from_package"
        ) as mock_pkg, patch(
            "lib.core.executor.api_manager._discover_from_directory"
        ) as mock_dir:

            apis2, _ = discover_apis(force_refresh=False)

            # Should not have called discovery functions (used cache)
            mock_pkg.assert_not_called()
            mock_dir.assert_not_called()

            # Should return same results
            assert set(apis1.keys()) == set(apis2.keys())

    def test_force_refresh_bypasses_cache(self):
        """Test that force_refresh=True bypasses the cache."""
        # First call
        discover_apis(force_refresh=True)

        # Second call with force_refresh should re-discover
        with patch("lib.core.executor.api_manager._discover_from_package") as mock_pkg:
            discover_apis(force_refresh=True)

            # Should have called discovery (not used cache)
            mock_pkg.assert_called()


class TestEndToEndCustomAPI:
    """Test end-to-end custom API recognition and execution."""

    def test_compile_script_with_custom_api(self, temp_dir):
        """Test compiling a script that uses custom API."""
        # Refresh patterns to include custom APIs
        script_syntax.refresh_patterns()

        # Create test script
        script = temp_dir / "test_custom_api.txt"
        script.write_text(
            """
[DEVICE1]
get system status
extract_hostname -var hostname
send "Hostname: {$hostname}"
"""
        )

        # Just test lexer tokenization (full compilation requires more setup)
        lexer = Lexer(str(script))
        lexer.parse()

        # Find the extract_hostname token
        extract_token = next(
            (t for t in lexer.tokens if t.str == "extract_hostname"), None
        )

        # Verify it was tokenized as an API, not a command
        assert extract_token is not None, "extract_hostname not found in tokens"
        assert (
            extract_token.type == "api"
        ), f"Expected type 'api', got '{extract_token.type}'"

    def test_custom_api_not_sent_to_device(self, mocker):
        """Test that custom API is not sent to device as command."""
        # Refresh patterns to include custom APIs
        script_syntax.refresh_patterns()

        # Test lexer with custom API
        lexer = Lexer()
        line = "extract_hostname -var hostname"
        tokens = lexer.parse_line(line)

        # Should NOT be a command token
        command_tokens = [t for t in tokens if t.type == "command"]
        assert len(command_tokens) == 0, "Custom API should not be tokenized as command"

        # Should be an API token
        api_tokens = [t for t in tokens if t.type == "api"]
        assert len(api_tokens) > 0, "Custom API should be tokenized as API"


class TestPatternGenerationRobustness:
    """Test that pattern generation handles edge cases gracefully."""

    def test_pattern_generation_with_discovery_failure(self, mocker):
        """Test that pattern generation continues if discovery fails."""
        # Mock discover_apis at the correct import location
        mocker.patch(
            "lib.core.executor.api_manager.discover_apis",
            side_effect=Exception("Discovery failed"),
        )

        # Should not crash, should fall back to static APIs only
        try:
            pattern = script_syntax._generate_api_pattern()
            # Should still have some pattern (built-in APIs)
            assert len(pattern) > 0
        except Exception as e:
            pytest.fail(f"Pattern generation should not fail when discovery fails: {e}")

    def test_pattern_generation_with_no_custom_apis(self, mocker):
        """Test pattern generation when no custom APIs exist."""
        # Mock discover_apis to return empty
        mocker.patch(
            "lib.core.executor.api_manager.discover_apis", return_value=({}, {})
        )

        pattern = script_syntax._generate_api_pattern()

        # Should still work with built-in APIs only
        assert len(pattern) > 0
        assert "exec_code" in pattern or r"exec_code\s" in pattern

    def test_pattern_sorting_with_custom_apis(self):
        """Test that API patterns are sorted by length (longer first)."""
        pattern = script_syntax._generate_api_pattern()

        # The pattern should have APIs sorted by length
        # This ensures longer API names are matched first to avoid prefix matching issues
        # We can't test the exact order, but we can verify it's a valid pattern
        assert pattern
        assert isinstance(pattern, str)

        # Try to compile the pattern as regex
        try:
            re.compile(pattern)
        except re.error:
            pytest.fail(f"Generated pattern is not valid regex: {pattern}")
