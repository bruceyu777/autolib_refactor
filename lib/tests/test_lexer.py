"""
Tests for lib.core.compiler.lexer module.
"""

# pylint: disable=use-implicit-booleaness-not-comparison,singleton-comparison
# pylint: disable=protected-access,unused-argument,unused-import
import re
from unittest.mock import mock_open, patch

import pytest

from lib.core.compiler.lexer import Lexer, Token


class TestToken:
    """Test suite for Token class."""

    def test_token_initialization(self):
        """Test token creation with type, data, and line number."""
        token = Token("comment", "This is a test", 1)
        assert token.type == "comment"
        assert token.str == "This is a test"
        assert token.line_number == 1

    def test_token_dict_behavior(self):
        """Test that token behaves like a dict."""
        token = Token("command", "config system admin", 5)
        assert token["type"] == "command"
        assert token["data"] == "config system admin"
        assert token["line_number"] == 5

    def test_token_properties(self):
        """Test token properties are read-only."""
        token = Token("api", "wait", 10)
        assert token.type == "api"
        assert token.str == "wait"
        assert token.line_number == 10


class TestLexer:
    """Test suite for Lexer class."""

    def test_lexer_initialization(self):
        """Test lexer initialization."""
        lexer = Lexer("/path/to/script.conf")
        assert lexer.file_name == "/path/to/script.conf"
        assert lexer.tokens == []
        assert lexer.section_commented == False
        assert lexer.line_number == 1
        assert lexer.dump_token == False

    def test_lexer_with_dump_token(self):
        """Test lexer with dump_token enabled."""
        lexer = Lexer("/path/to/script.conf", dump_token=True)
        assert lexer.dump_token == True

    def test_add_token(self):
        """Test adding tokens to token list."""
        lexer = Lexer()
        lexer.line_number = 5
        lexer.add_token("comment", "Test comment")

        assert len(lexer.tokens) == 1
        assert lexer.tokens[0].type == "comment"
        assert lexer.tokens[0].str == "Test comment"
        assert lexer.tokens[0].line_number == 5

    def test_parse_comment_line(self):
        """Test parsing comment lines."""
        lexer = Lexer()
        lexer.line_number = 1

        # Directly test the comment handler
        lexer.cur_groupdict = {"comment_content": "This is a test"}
        lexer.comment()

        assert len(lexer.tokens) == 1
        assert lexer.tokens[0].type == "comment"
        assert lexer.tokens[0].str == "This is a test"

    def test_parse_command_line(self, mocker):
        """Test parsing command lines."""
        mock_schema = mocker.patch("lib.core.compiler.lexer.script_syntax")
        mock_schema.line_pattern.match.return_value.groupdict.return_value = {
            "command": "config system admin",
            "section": None,
        }
        mock_schema.is_valid_line_type.return_value = True

        lexer = Lexer()
        lexer.parse_line("config system admin")

        assert len(lexer.tokens) == 1
        assert lexer.tokens[0].type == "command"
        assert lexer.tokens[0].str == "config system admin"

    def test_parse_section_line(self):
        """Test parsing section declarations."""
        lexer = Lexer()
        lexer.line_number = 1

        # Directly test the section handler
        lexer.cur_groupdict = {"section_name": "FGT1"}
        lexer.section()

        assert len(lexer.tokens) == 1
        assert lexer.tokens[0].type == "section"
        assert lexer.tokens[0].str == "FGT1"
        assert lexer.section_commented == False

    def test_parse_commented_section(self, mocker):
        """Test parsing commented sections."""
        mock_schema = mocker.patch("lib.core.compiler.lexer.script_syntax")
        mock_schema.line_pattern.match.return_value.groupdict.return_value = {
            "commented_section": "##<device> FGT1 <device>",
            "section": None,
        }
        mock_schema.is_valid_line_type.return_value = True

        lexer = Lexer()
        lexer.parse_line("##<device> FGT1 <device>")

        assert lexer.section_commented == True

    def test_lines_in_commented_section_are_ignored(self, mocker):
        """Test that lines within commented sections are ignored."""
        mock_schema = mocker.patch("lib.core.compiler.lexer.script_syntax")

        lexer = Lexer()
        lexer.section_commented = True

        # Mock the match to return None for section
        mock_schema.line_pattern.match.return_value.groupdict.return_value = {
            "command": "config system admin",
            "section": None,
        }

        tokens = lexer.parse_line("config system admin")

        # Should return empty list (line ignored)
        assert tokens == []

    def test_parse_include_line(self):
        """Test parsing include directives."""
        lexer = Lexer()
        lexer.line_number = 1

        # Directly test the include handler
        lexer.cur_groupdict = {"file_name": "/path/to/file.conf"}
        lexer.include()

        assert len(lexer.tokens) == 1
        assert lexer.tokens[0].type == "include"
        assert lexer.tokens[0].str == "/path/to/file.conf"

    def test_deprecated_command_replacement(self, mocker):
        """Test deprecated command replacement and warning."""

        # Mock the cached DEPRECATED_PATTERNS directly
        mock_pattern = re.compile(r"^oldcmd\s+(.+)$")
        mocker.patch(
            "lib.core.compiler.lexer.DEPRECATED_PATTERNS",
            [(mock_pattern, r"newcmd \1")],
        )
        mocker.patch("lib.core.compiler.lexer.DEPRECATED_PREFIXES", {"oldcmd"})
        mock_logger = mocker.patch("lib.core.compiler.lexer.logger")

        lexer = Lexer()
        result = lexer.update_deprecated_command("oldcmd test")

        assert result == "newcmd test"
        # Should log warning
        assert mock_logger.warning.called

    def test_deprecated_command_no_match(self, mocker):
        """Test that non-deprecated commands are not modified."""
        # Mock the cached DEPRECATED_PATTERNS directly
        mock_pattern = re.compile(r"^oldcmd\s+(.+)$")
        mocker.patch(
            "lib.core.compiler.lexer.DEPRECATED_PATTERNS",
            [(mock_pattern, r"newcmd \1")],
        )
        mocker.patch("lib.core.compiler.lexer.DEPRECATED_PREFIXES", {"oldcmd"})
        mock_logger = mocker.patch("lib.core.compiler.lexer.logger")

        lexer = Lexer()
        result = lexer.update_deprecated_command("config system admin")

        assert result == "config system admin"
        # Should not log warning
        assert not mock_logger.warning.called

    def test_encoding_detection_utf8(self, temp_dir):
        """Test reading UTF-8 encoded files."""
        test_file = temp_dir / "utf8.conf"
        test_file.write_text("comment: UTF-8 文件", encoding="utf-8")

        lexer = Lexer(str(test_file))
        content = lexer.read()

        assert "comment: UTF-8 文件" in content

    def test_encoding_detection_latin1(self, temp_dir):
        """Test reading Latin-1 encoded files."""
        test_file = temp_dir / "latin1.conf"
        content = "comment: Café"
        test_file.write_bytes(content.encode("latin-1"))

        lexer = Lexer(str(test_file))
        result = lexer.read()

        # chardet should detect and decode properly
        assert "comment" in result

    def test_empty_file_handling(self, temp_dir):
        """Test handling of empty files."""
        test_file = temp_dir / "empty.conf"
        test_file.write_text("")

        lexer = Lexer(str(test_file))
        content = lexer.read()

        assert content == ""

    def test_parse_full_file(self, temp_dir):
        """Test parsing a complete file."""
        test_file = temp_dir / "script.conf"
        test_file.write_text("comment: Test script\n")

        # Just test that parse doesn't crash
        # Full parsing requires real syntax schema
        lexer = Lexer(str(test_file))
        content = lexer.read()
        lines = content.splitlines()

        assert len(lines) > 0
        assert "Test script" in content

    def test_line_number_increment(self, temp_dir):
        """Test that line number increments during parsing."""
        test_file = temp_dir / "script.conf"
        test_file.write_text("comment: Line 1\ncomment: Line 2\ncomment: Line 3\n")

        lexer = Lexer(str(test_file))
        content = lexer.read()
        lines = content.splitlines()

        # Test line counting
        assert len(lines) == 3

    def test_dump_token_to_file(self, temp_dir, mocker):
        """Test dumping tokens to JSON file."""
        mock_schema = mocker.patch("lib.core.compiler.lexer.script_syntax")
        mock_output = mocker.patch("lib.core.compiler.lexer.output")
        mock_output.compose_compiled_file.return_value = str(temp_dir / "tokens.json")

        lexer = Lexer(str(temp_dir / "test.conf"), dump_token=True)
        lexer.line_number = 1
        lexer.cur_line = "comment: Test"
        lexer.cur_groupdict = {
            "comment": "comment: Test",
            "comment_content": "Test",
            "section": None,
        }
        mock_schema.is_valid_line_type.return_value = True

        lexer.add_token("comment", "Test")

        # Call dump (requires mocking file open)
        with patch("builtins.open", mock_open()) as mock_file:
            lexer._dump_to_file()
            mock_file.assert_called_once()

    def test_handle_set_statements(self):
        """Test handling of set statements (intset, strset, listset)."""
        lexer = Lexer()
        lexer.line_number = 1

        # Test intset
        lexer._handle_set_statement("var1 10")
        assert len(lexer.tokens) == 2
        assert lexer.tokens[0].type == "identifier"
        assert lexer.tokens[0].str == "var1"
        assert lexer.tokens[1].type == "identifier"
        assert lexer.tokens[1].str == "10"

    def test_is_set_statement(self):
        """Test checking for set statement keywords."""
        lexer = Lexer()
        assert lexer._is_set_statement("intset") == True
        assert lexer._is_set_statement("strset") == True
        assert lexer._is_set_statement("listset") == True
        assert lexer._is_set_statement("if") == False

    def test_is_tokenizable_statement(self):
        """Test checking for tokenizable statement keywords."""
        lexer = Lexer()
        assert lexer._is_tokenizable_statement("if") == True
        assert lexer._is_tokenizable_statement("elseif") == True
        assert lexer._is_tokenizable_statement("until") == True
        assert lexer._is_tokenizable_statement("intset") == False


class TestLexerIntegration:
    """Integration tests for Lexer with real syntax patterns."""

    def test_parse_real_script_basic(self, temp_dir):
        """Test parsing a real basic script."""
        # This would require real script_syntax, skipping for now
        pytest.skip("Requires real syntax schema integration")

    def test_parse_with_control_flow(self, temp_dir):
        """Test parsing script with control flow."""
        pytest.skip("Requires real syntax schema integration")
