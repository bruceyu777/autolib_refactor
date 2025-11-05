"""
Tests for lib.core.compiler.compiler module.
"""

# pylint: disable=use-implicit-booleaness-not-comparison,protected-access
# pylint: disable=unused-argument,no-else-return,unused-import

import threading
from unittest.mock import MagicMock

import pytest

from lib.core.compiler.compiler import Compiler, compiler
from lib.core.compiler.vm_code import VMCode


class TestCompiler:
    """Test suite for Compiler class."""

    def test_compiler_is_singleton(self):
        """Test that compiler is a singleton instance."""
        assert compiler is not None
        assert isinstance(compiler, Compiler)

    def test_compiler_initialization(self):
        """Test compiler initialization."""
        c = Compiler()
        assert c.files == {}
        assert c.devices == set()
        assert c._lock is not None

    def test_compile_file_basic(self, temp_script_file, mocker):
        """Test basic file compilation."""
        # Mock the lexer and parser
        mock_lexer = mocker.patch("lib.core.compiler.compiler.Lexer")
        mock_parser = mocker.patch("lib.core.compiler.compiler.Parser")

        # Setup mock returns
        mock_tokens = [MagicMock()]
        mock_lines = ["comment: test"]
        mock_vm_codes = [VMCode(1, "comment", ["test"])]
        mock_devices = {"FGT1", "FGT2"}
        mock_called_files = []

        mock_lexer.return_value.parse.return_value = (mock_tokens, mock_lines)
        mock_parser.return_value.run.return_value = (
            mock_vm_codes,
            mock_devices,
            mock_called_files,
        )

        c = Compiler()
        c.run(str(temp_script_file))

        # Verify compilation happened
        assert str(temp_script_file) in c.files
        assert c.devices == mock_devices
        assert c.files[str(temp_script_file)] == mock_vm_codes

    def test_compile_file_caching(self, temp_script_file, mocker):
        """Test that compilation results are cached."""
        mock_lexer = mocker.patch("lib.core.compiler.compiler.Lexer")
        mock_parser = mocker.patch("lib.core.compiler.compiler.Parser")

        mock_tokens = [MagicMock()]
        mock_lines = ["comment: test"]
        mock_vm_codes = [VMCode(1, "comment", ["test"])]

        mock_lexer.return_value.parse.return_value = (mock_tokens, mock_lines)
        mock_parser.return_value.run.return_value = (mock_vm_codes, set(), [])

        c = Compiler()

        # Compile twice
        c.run(str(temp_script_file))
        c.run(str(temp_script_file))

        # Lexer should only be called once (cached)
        assert mock_lexer.call_count == 1

    def test_compile_file_with_includes(self, temp_dir, mocker):
        """Test compilation with included files."""
        # Create main file and included file
        included_file = temp_dir / "included.conf"
        included_file.write_text("comment: Included file\nconfig system global\nend\n")

        main_file = temp_dir / "main.conf"
        main_file.write_text(f"comment: Main file\ninclude {included_file}\n")

        mock_lexer = mocker.patch("lib.core.compiler.compiler.Lexer")
        mock_parser = mocker.patch("lib.core.compiler.compiler.Parser")
        mock_env = mocker.patch("lib.core.compiler.compiler.env")

        # Mock variable interpolation to return the path as-is
        mock_env.variable_interpolation.return_value = str(included_file)

        mock_tokens = [MagicMock()]
        mock_lines = ["comment: test"]

        # Setup different returns for main and included files
        call_count = [0]

        def mock_parse_side_effect(*args, **kwargs):
            call_count[0] += 1
            return (mock_tokens, mock_lines)

        def mock_run_side_effect(*args, **kwargs):
            if call_count[0] == 1:  # Main file
                return (
                    [VMCode(1, "comment", ["Main file"])],
                    set(),
                    [(str(included_file), None)],  # Called file
                )
            else:  # Included file
                return (
                    [VMCode(1, "comment", ["Included file"])],
                    set(),
                    [],  # No more includes
                )

        mock_lexer.return_value.parse.side_effect = mock_parse_side_effect
        mock_parser.return_value.run.side_effect = mock_run_side_effect

        c = Compiler()
        c.run(str(main_file))

        # Both files should be compiled
        assert str(main_file) in c.files
        assert str(included_file) in c.files
        assert mock_lexer.call_count == 2

    def test_compile_file_thread_safety(self, temp_dir, mocker):
        """Test thread-safe compilation."""
        # Create multiple script files
        files = []
        for i in range(5):
            f = temp_dir / f"script{i}.conf"
            f.write_text(f"comment: Script {i}\n")
            files.append(str(f))

        mock_lexer = mocker.patch("lib.core.compiler.compiler.Lexer")
        mock_parser = mocker.patch("lib.core.compiler.compiler.Parser")

        mock_tokens = [MagicMock()]
        mock_lines = ["comment: test"]
        mock_vm_codes = [VMCode(1, "comment", ["test"])]

        mock_lexer.return_value.parse.return_value = (mock_tokens, mock_lines)
        mock_parser.return_value.run.return_value = (mock_vm_codes, set(), [])

        c = Compiler()

        # Compile files in parallel
        threads = []
        for f in files:
            t = threading.Thread(target=c.run, args=(f,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All files should be compiled once
        assert len(c.files) == 5
        for f in files:
            assert f in c.files

    def test_retrieve_vm_codes_returns_copy(self, temp_script_file, mocker):
        """Test that retrieve_vm_codes returns a deep copy."""
        mock_lexer = mocker.patch("lib.core.compiler.compiler.Lexer")
        mock_parser = mocker.patch("lib.core.compiler.compiler.Parser")

        mock_tokens = [MagicMock()]
        mock_lines = ["comment: test"]
        mock_vm_codes = [VMCode(1, "command", ["config system global"])]

        mock_lexer.return_value.parse.return_value = (mock_tokens, mock_lines)
        mock_parser.return_value.run.return_value = (mock_vm_codes, set(), [])

        c = Compiler()
        c.run(str(temp_script_file))

        # Retrieve vm codes twice
        codes1 = c.retrieve_vm_codes(str(temp_script_file))
        codes2 = c.retrieve_vm_codes(str(temp_script_file))

        # Should be different objects (deep copy)
        assert codes1 is not codes2
        assert codes1[0] is not codes2[0]

        # But equal in value
        assert codes1[0].line_number == codes2[0].line_number
        assert codes1[0].operation == codes2[0].operation

    def test_retrieve_devices(self, temp_script_file, mocker):
        """Test retrieving discovered devices."""
        mock_lexer = mocker.patch("lib.core.compiler.compiler.Lexer")
        mock_parser = mocker.patch("lib.core.compiler.compiler.Parser")

        mock_tokens = [MagicMock()]
        mock_lines = ["comment: test"]
        mock_vm_codes = [VMCode(1, "comment", ["test"])]
        mock_devices = {"FGT1", "FGT2", "FGT3"}

        mock_lexer.return_value.parse.return_value = (mock_tokens, mock_lines)
        mock_parser.return_value.run.return_value = (mock_vm_codes, mock_devices, [])

        c = Compiler()
        c.run(str(temp_script_file))

        devices = c.retrieve_devices()
        assert devices == mock_devices

    def test_compile_accumulates_devices(self, temp_dir, mocker):
        """Test that devices from multiple files are accumulated."""
        file1 = temp_dir / "script1.conf"
        file1.write_text("comment: Script 1\n")

        file2 = temp_dir / "script2.conf"
        file2.write_text("comment: Script 2\n")

        mock_lexer = mocker.patch("lib.core.compiler.compiler.Lexer")
        mock_parser = mocker.patch("lib.core.compiler.compiler.Parser")

        mock_tokens = [MagicMock()]
        mock_lines = ["comment: test"]

        call_count = [0]

        def mock_run_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return ([VMCode(1, "comment", ["test"])], {"FGT1", "FGT2"}, [])
            else:
                return ([VMCode(1, "comment", ["test"])], {"FGT3", "FGT4"}, [])

        mock_lexer.return_value.parse.return_value = (mock_tokens, mock_lines)
        mock_parser.return_value.run.side_effect = mock_run_side_effect

        c = Compiler()
        c.run(str(file1))
        c.run(str(file2))

        # Devices should be accumulated
        assert c.devices == {"FGT1", "FGT2", "FGT3", "FGT4"}

    def test_compile_in_debug_mode(self, temp_script_file, mocker, mock_logger):
        """Test compilation with debug mode enabled."""
        # Enable debug mode
        mock_logger.in_debug_mode = True

        mock_lexer_cls = mocker.patch("lib.core.compiler.compiler.Lexer")
        mock_parser_cls = mocker.patch("lib.core.compiler.compiler.Parser")

        mock_tokens = [MagicMock()]
        mock_lines = ["comment: test"]
        mock_vm_codes = [VMCode(1, "comment", ["test"])]

        mock_lexer_cls.return_value.parse.return_value = (mock_tokens, mock_lines)
        mock_parser_cls.return_value.run.return_value = (mock_vm_codes, set(), [])

        c = Compiler()
        c.run(str(temp_script_file))

        # Verify debug flags were passed
        mock_lexer_cls.assert_called_once_with(str(temp_script_file), dump_token=True)
        mock_parser_cls.return_value.run.assert_called_once_with(dump_code_flag=True)

    def test_compile_double_check_locking(self, temp_script_file, mocker):
        """Test double-check locking pattern in _compile_file."""
        mock_lexer = mocker.patch("lib.core.compiler.compiler.Lexer")
        mock_parser = mocker.patch("lib.core.compiler.compiler.Parser")

        mock_tokens = [MagicMock()]
        mock_lines = ["comment: test"]
        mock_vm_codes = [VMCode(1, "comment", ["test"])]

        mock_lexer.return_value.parse.return_value = (mock_tokens, mock_lines)
        mock_parser.return_value.run.return_value = (mock_vm_codes, set(), [])

        c = Compiler()

        # Manually add file to cache
        c.files[str(temp_script_file)] = mock_vm_codes

        # Try to compile again
        c._compile_file(str(temp_script_file))

        # Lexer should not be called (already cached)
        mock_lexer.assert_not_called()

    def test_compile_with_device_context_in_include(self, temp_dir, mocker):
        """Test include with device context for variable interpolation."""
        included_file = temp_dir / "included.conf"
        included_file.write_text("comment: Included\n")

        main_file = temp_dir / "main.conf"
        main_file.write_text(f"include {included_file}\n")

        mock_lexer = mocker.patch("lib.core.compiler.compiler.Lexer")
        mock_parser = mocker.patch("lib.core.compiler.compiler.Parser")
        mock_env = mocker.patch("lib.core.compiler.compiler.env")

        mock_env.variable_interpolation.return_value = str(included_file)

        mock_tokens = [MagicMock()]
        mock_lines = ["comment: test"]

        call_count = [0]

        def mock_run_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # Main file with device context in include
                return (
                    [VMCode(1, "include", [str(included_file)])],
                    set(),
                    [(str(included_file), "FGT1")],  # Include with device context
                )
            else:
                return ([VMCode(1, "comment", ["Included"])], set(), [])

        mock_lexer.return_value.parse.return_value = (mock_tokens, mock_lines)
        mock_parser.return_value.run.side_effect = mock_run_side_effect

        c = Compiler()
        c.run(str(main_file))

        # Variable interpolation should be called with device context
        mock_env.variable_interpolation.assert_called_with(
            str(included_file), current_device="FGT1"
        )


class TestCompilerIntegration:
    """Integration tests for Compiler with real Lexer and Parser."""

    def test_full_compilation_pipeline(self, temp_script_file):
        """Test full compilation from file to vm_codes."""
        # This would need actual Lexer and Parser, skipping for now
        # as it requires complex mocking of syntax schema
        pytest.skip("Requires real Lexer/Parser integration")
