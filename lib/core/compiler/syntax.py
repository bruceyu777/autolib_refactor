"""
Unified syntax module - loads ALL data from enhanced schema.

Single source of truth: cli_syntax.json contains:
- APIs with parameters
- Valid FortiOS commands
- Script types
- Deprecated command patterns
- Control flow keywords

Zero hardcoded data in Python code!
"""

import json
import re
from collections import OrderedDict

from lib.services import logger

from .schema_loader import get_schema_registry
from .settings import SYNTAX_DEFINITION_FILEPATH


class ScriptSyntax:
    """
    Script syntax definitions and patterns.

    All data loaded from cli_syntax.json - zero hardcoded definitions!
    """

    # Token patterns (lexer-level, not in schema)
    TOKEN_PATTERN_TABLE = {
        "variable": r"\{?\$(?P<variable_name>[^\s]+?)\s*\}?",
        "symbol": r"==|[-()[\]{}<>+*\/=]",
        "number": r"(?P<number_content>\d+)",
        "operator": r"eq|ne|lt",
        "expect_double": r'\-e\s+"(?P<double_quote_str>[^\"]*)"(?=\s+\-)',
        "expect_single": r"\-e\s+'(?P<single_quote_str>[^\']*)'(?=\s+\-)",
        "expect_string": r"\-e\s+(?P<expect_str>\S*)(?=\s+\-)",
        "string": r'"(?:\"|[^"\\]|\\.)*?"',
        "identifier": r"\{.+\}|.+?",
    }

    # Line patterns (lexer-level, generated from schema)
    LINE_PATTERN_TABLE = {
        "commented_section": r"#\s*\[[A-Z_0-9]+\]",
        "commented_line": r"#.*",
        "section": r"\[(?P<section_name>[A-Z_0-9]+)\]",
        "statement": "",  # Generated from keywords
        "comment": r"[Cc]omment[s]*\s*:*\s*(?P<comment_content>.*)",
        "include": r"include\s+(?P<file_name>.+)",
        "api": "",  # Generated from APIs
        "command": r".+",
    }

    OPERATOR_TOKEN_TYPE = ["operator", "symbol"]

    def __init__(self, syntax_filepath):
        """Initialize with enhanced unified schema."""
        with open(syntax_filepath, "r", encoding="utf-8") as f:
            self.schema = json.load(f, object_pairs_hook=OrderedDict)

        # Validate schema format
        required_sections = [
            "apis",
            "valid_commands",
            "script_types",
            "deprecated_commands",
            "keywords",
        ]
        for section in required_sections:
            if section not in self.schema:
                raise ValueError(f"Schema must have '{section}' section")

        # PERFORMANCE: Cache tuple for is_valid_command() to avoid repeated tuple() calls
        # This eliminates ~150 tuple creations per 100 scripts (2-3% speedup)
        self._valid_commands_tuple = tuple(self.schema["valid_commands"])

        # PHASE 1: Generate patterns with static APIs only (avoid circular import)
        # Custom APIs from plugins/apis/ are added later via refresh_patterns()
        self.line_pattern = self._generate_static_line_pattern()
        self.token_pattern = self.generate_token_pattern()

    def get_deprecated_cmd_replace_patterns(self):
        return self.schema["deprecated_commands"]

    def is_valid_command(self, command):
        return command.startswith(self._valid_commands_tuple)

    def is_valid_script_type(self, script_type):
        return script_type in self.schema["script_types"]

    def is_valid_line_type(self, line_type):
        return line_type in self.LINE_PATTERN_TABLE

    def is_valid_token_type(self, token_type):
        return token_type in self.TOKEN_PATTERN_TABLE

    def at_top_level_category(self, category):
        return category in ["api", "keyword"]

    def get_token_syntax_definition(self, token):
        """
        Get parsing definition for a token.

        Returns (operation, matched_rule) tuple for parser.
        All data extracted from unified schema.
        """
        token_type = token.type
        token_str = token.str

        if token_type == "api":
            return self._get_api_syntax_definition(token_str)

        if token_type == "keyword":
            return self._get_keyword_syntax_definition(token_str)

        return None

    def _get_api_syntax_definition(self, api_name):
        api_schema = self.schema["apis"].get(api_name)
        if not api_schema:
            return None

        parse_mode = api_schema.get("parse_mode", "positional")

        if parse_mode == "options":
            return self._build_options_syntax(api_schema)

        if parse_mode == "positional":
            return self._build_positional_syntax(api_schema)

        return None

    def _build_options_syntax(self, api_schema):
        options_dict = {}
        params = api_schema.get("parameters", {})

        # Sort parameters by position to ensure tuple order matches ApiParams expectations
        # This prevents bugs when JSON schemas have parameters in non-position order
        sorted_params = sorted(
            params.items(), key=lambda item: item[1].get("position", 999)
        )

        for option, param_def in sorted_params:
            default = param_def.get("default")
            options_dict[option] = default

        # Standard option parsing rule
        option_rule = [
            ["identifier", None],
            [["identifier", "number", "string", "variable", "operator"], None],
        ]

        return ("parse_options", [options_dict, option_rule])

    def _build_positional_syntax(self, api_schema):
        params = api_schema.get("parameters", [])

        if not params:
            return ("parse", [])

        # Build token rules for each parameter
        param_rules = []
        type_mapping = {
            "string": [
                "string",  # Accept quoted strings like "admin\\n"
                "identifier",  # Accept unquoted identifiers
                "number",  # Strings can be numeric (e.g., "801830")
                "variable",
            ],
            "int": ["number"],
            "number": ["number"],
            "bool": ["identifier"],
        }

        for param in params:
            param_type = param.get("type", "string")
            legacy_types = type_mapping.get(param_type, ["identifier"])
            param_rules.append([legacy_types, None])

        return ("parse", param_rules)

    def _get_keyword_syntax_definition(self, keyword):
        keyword_def = self.schema["keywords"].get(keyword)
        if not keyword_def:
            return None

        keyword_type = keyword_def.get("type")

        if keyword_type == "control_block":
            flow = keyword_def.get("flow", [])
            return ("control_block", flow)

        if keyword_type == "parse":
            rules = keyword_def.get("rules", [])
            return ("parse", rules)

        return None

    def get_keyword_cli_syntax(self, keyword):
        keyword_def = self.schema["keywords"].get(keyword)
        if keyword_def:
            return keyword_def.get("flow", [])
        return None

    def _generate_keyword_pattern(self):
        keywords = self.schema["keywords"].keys()
        sorted_keywords = sorted(keywords, key=len, reverse=True)
        return "|".join(rf"{keyword}" for keyword in sorted_keywords)

    def _generate_statement_pattern(self):
        keyword_pattern = self._generate_keyword_pattern()
        return rf"\<\s*(?P<statement_content>({keyword_pattern}).*)\>"

    @staticmethod
    def _has_required_parameter(params):
        if isinstance(params, dict):
            return any(p.get("required", False) for p in params.values())
        if isinstance(params, list):
            return any(p.get("required", False) for p in params)
        return False

    @staticmethod
    def _create_default_api_schema():
        """
        Create default schema for dynamically discovered custom APIs.

        Custom APIs default to "options" parse mode with common parameters.
        The schema includes standard options like -var that most custom APIs use.
        APIs can use any of these options, and the parser will handle them correctly.
        """
        return {
            "category": "custom",
            "parse_mode": "options",
            "parameters": {
                # Common parameter used by most custom APIs
                "-var": {
                    "alias": "var",
                    "type": "string",
                    "position": 0,
                    "required": False,
                    "description": "Variable name to store result",
                },
                # Additional common parameters can be added here
                "-file": {
                    "alias": "file",
                    "type": "string",
                    "position": 1,
                    "required": False,
                    "description": "File path parameter",
                },
                "-value": {
                    "alias": "value",
                    "type": "string",
                    "position": 2,
                    "required": False,
                    "description": "Value parameter",
                },
                "-name": {
                    "alias": "name",
                    "type": "string",
                    "position": 3,
                    "required": False,
                    "description": "Name parameter",
                },
            },
            "description": "Dynamically discovered custom API",
        }

    def _api_pattern(self, api_name):
        """Generate pattern for API using schema from self.schema."""
        api_schema = self.schema["apis"][api_name]
        return self._api_pattern_for_api(api_name, api_schema)

    def _api_pattern_for_api(self, api_name, api_schema):
        """
        Generate regex pattern for a specific API given its schema.

        Args:
            api_name: Name of the API
            api_schema: Schema dict for the API

        Returns:
            Regex pattern string for matching this API
        """
        params = api_schema.get("parameters", {})
        if ScriptSyntax._has_required_parameter(params):
            return rf"{api_name}\s+.+"
        if len(params) > 0:
            return rf"{api_name}\s*.*"
        return f"{api_name}"

    def _generate_api_pattern(self):
        """
        Generate API pattern (delegates to static version).

        Use refresh_patterns() to include custom APIs after module initialization.
        """
        return self._generate_static_api_pattern()

    def _generate_static_api_pattern(self):
        """
        Generate API pattern from static schema only (no dynamic discovery).

        Returns pattern for built-in APIs defined in cli_syntax.json.
        Custom APIs are added later via refresh_patterns().
        """
        api_pattern_list = [
            self._api_pattern(api_name) for api_name in self.schema["apis"]
        ]
        api_pattern_list = sorted(api_pattern_list, key=len, reverse=True)
        return r"|".join(api_pattern_list)

    def _generate_static_line_pattern(self):
        """
        Generate line pattern using only static APIs from schema.

        Used during module initialization to avoid circular imports.
        Call refresh_patterns() after all modules loaded to include custom APIs.
        """
        ScriptSyntax.LINE_PATTERN_TABLE["statement"] = (
            self._generate_statement_pattern()
        )
        ScriptSyntax.LINE_PATTERN_TABLE["api"] = self._generate_static_api_pattern()
        line_pattern = re.compile(
            r"|".join(
                rf"(?P<{type}>{pattern})"
                for type, pattern in ScriptSyntax.LINE_PATTERN_TABLE.items()
            )
        )
        return line_pattern

    def generate_line_pattern(self):
        """
        Generate line pattern (delegates to static version).

        Use refresh_patterns() to include custom APIs.
        """
        ScriptSyntax.LINE_PATTERN_TABLE["statement"] = (
            self._generate_statement_pattern()
        )
        ScriptSyntax.LINE_PATTERN_TABLE["api"] = self._generate_api_pattern()
        line_pattern = re.compile(
            r"|".join(
                rf"(?P<{type}>{pattern})"
                for type, pattern in ScriptSyntax.LINE_PATTERN_TABLE.items()
            )
        )
        # Update instance variable so lexer uses the new pattern
        self.line_pattern = line_pattern
        return line_pattern

    def refresh_patterns(self):
        """
        Refresh patterns to include dynamically discovered custom APIs.

        This should be called after all modules are loaded (e.g., from Compiler
        initialization) to discover custom APIs from plugins/apis/ and include
        them in the lexer patterns.

        Safe to call multiple times - will regenerate patterns each time.
        """
        try:
            # Import after all modules loaded to prevent circular import
            # pylint: disable=import-outside-toplevel
            from lib.core.executor.api_manager import discover_apis

            logger.debug("Discovering custom APIs for pattern generation...")
            discovered_apis, _ = discover_apis()

            # Merge static APIs with discovered custom APIs
            all_apis = dict(self.schema["apis"])

            custom_count = 0
            for api_name in discovered_apis:
                if api_name not in all_apis:
                    logger.debug("Apply default schema for custom API: %s", api_name)
                    all_apis[api_name] = self._create_default_api_schema()
                    custom_count += 1

            logger.info(
                "Pattern refresh: %d total APIs (%d custom)",
                len(all_apis),
                custom_count,
            )

            # Update schema with ALL APIs (needed for parser's _get_api_syntax_definition)
            self.schema["apis"] = all_apis

            # IMPORTANT: Register custom APIs with schema_loader
            # so get_schema() can find them at runtime (for ApiParams)
            # pylint: disable=import-outside-toplevel
            schema_registry = get_schema_registry()

            for api_name in discovered_apis:
                if api_name not in schema_registry._schemas:
                    schema_registry.register_schema(api_name, all_apis[api_name])
                    logger.debug("Registered custom API schema: %s", api_name)

            # Regenerate API pattern with ALL APIs
            api_pattern_list = [
                self._api_pattern_for_api(api_name, all_apis[api_name])
                for api_name in all_apis
            ]
            api_pattern_list = sorted(api_pattern_list, key=len, reverse=True)
            ScriptSyntax.LINE_PATTERN_TABLE["api"] = r"|".join(api_pattern_list)

            # Recompile line pattern
            self.line_pattern = re.compile(
                r"|".join(
                    rf"(?P<{type}>{pattern})"
                    for type, pattern in ScriptSyntax.LINE_PATTERN_TABLE.items()
                )
            )

            logger.debug("Pattern refresh complete")

        except Exception as e:  # pylint: disable=broad-except
            logger.error("Failed to refresh patterns with custom APIs: %s", e)
            logger.error("Custom APIs will not be recognized. Using static APIs only.")
            # Don't raise - fallback to static APIs is acceptable

    def generate_token_pattern(self):
        token_pattern_table = ScriptSyntax.TOKEN_PATTERN_TABLE
        token_pattern = re.compile(
            r"|".join(
                rf"(?P<{type}>{pattern})(\s+|$)"
                for type, pattern in token_pattern_table.items()
            )
        )
        return token_pattern


# Singleton instance
script_syntax = ScriptSyntax(SYNTAX_DEFINITION_FILEPATH)
