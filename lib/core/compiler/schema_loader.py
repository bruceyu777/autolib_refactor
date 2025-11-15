"""
Schema loader and registry for API parameter validation.

This module provides schema-driven parameter validation and type conversion,
serving as the contract layer between compiler and runtime.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from lib.services import logger

from .settings import SYNTAX_DEFINITION_FILEPATH


@dataclass
class ParameterSchema:
    """Schema definition for a single API parameter."""

    name: str
    type: str  # "string", "int", "number", "bool"
    required: bool = True
    default: Any = None
    option: Optional[str] = None  # CLI flag like "-e", "-for"
    position: Optional[int] = None  # Position in tuple
    enum: Optional[List[str]] = None
    description: str = ""

    def validate_and_cast(self, value: Any) -> Any:
        """
        Validate and cast value to correct type.

        Args:
            value: Raw value from parser

        Returns:
            Validated and type-cast value

        Raises:
            ValueError: If validation fails
        """
        if value is None:
            if self.required:
                raise ValueError(f"Required parameter '{self.name}' is missing")
            return self.default

        # Enum validation
        if self.enum and value not in self.enum:
            raise ValueError(
                f"Parameter '{self.name}' must be one of {self.enum}, got '{value}'"
            )

        # Type casting
        if self.type in ("int", "number"):
            try:
                return int(value)
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"Parameter '{self.name}' must be an integer, got '{value}'"
                ) from e
        elif self.type == "bool":
            if isinstance(value, str):
                return value.lower() in ("true", "yes", "1")
            return bool(value)
        elif self.type == "string":
            return str(value) if value is not None else None
        else:
            return value


@dataclass
class APISchema:
    """Complete schema definition for an API."""

    name: str
    description: str
    category: str
    parse_mode: str  # "positional", "options", "mixed"
    parameters: List[ParameterSchema]

    @classmethod
    def from_dict(cls, api_name: str, schema_dict: dict) -> "APISchema":
        """
        Load API schema from dictionary.

        Args:
            api_name: Name of the API
            schema_dict: Schema definition dict

        Returns:
            APISchema instance
        """
        params = []

        # Handle list-based parameters (new format)
        if isinstance(schema_dict.get("parameters"), list):
            for param_def in schema_dict["parameters"]:
                params.append(
                    ParameterSchema(
                        name=param_def["name"],
                        type=param_def.get("type", "string"),
                        required=param_def.get("required", True),
                        default=param_def.get("default"),
                        option=param_def.get("option"),
                        position=param_def.get("position"),
                        enum=param_def.get("enum"),
                        description=param_def.get("description", ""),
                    )
                )
        # Handle dict-based parameters (options format)
        elif isinstance(schema_dict.get("parameters"), dict):
            for i, (key, param_def) in enumerate(schema_dict["parameters"].items()):
                params.append(
                    ParameterSchema(
                        name=param_def.get("alias", key),
                        type=param_def.get("type", "string"),
                        required=param_def.get("required", True),
                        default=param_def.get("default"),
                        option=key,
                        position=param_def.get("position", i),
                        enum=param_def.get("enum"),
                        description=param_def.get("description", ""),
                    )
                )

        # Sort by position if positional/mixed mode
        parse_mode = schema_dict.get("parse_mode", "positional")
        if parse_mode in ("positional", "mixed"):
            params.sort(key=lambda p: p.position if p.position is not None else 999)

        return cls(
            name=api_name,
            description=schema_dict.get("description", ""),
            category=schema_dict.get("category", "general"),
            parse_mode=parse_mode,
            parameters=params,
        )

    def get_param_order(self) -> List[str]:
        """Get parameter names in positional order."""
        if self.parse_mode == "options":
            return [
                p.name for p in sorted(self.parameters, key=lambda x: x.position or 0)
            ]
        return [p.name for p in self.parameters]

    def get_aliases(self) -> Dict[str, str]:
        """Get mapping from CLI options to parameter names."""
        return {p.option: p.name for p in self.parameters if p.option}

    def validate_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and type-cast all parameters.

        Args:
            params: Dict of parameter names to values

        Returns:
            Validated and type-cast parameters dict
        """
        result = {}
        for param_schema in self.parameters:
            value = params.get(param_schema.name)
            result[param_schema.name] = param_schema.validate_and_cast(value)
        return result

    def get_help(self) -> str:
        """Generate help text for this API."""
        lines = [
            f"Category: {self.category}",
            f"Parse Mode: {self.parse_mode}",
            f"Description: {self.description}",
            "",
            "Parameters:",
        ]

        for param in self.parameters:
            req = "required" if param.required else "optional"
            default = (
                f" (default: {param.default})" if param.default is not None else ""
            )

            if self.parse_mode == "options":
                option = f" [{param.option}]" if param.option else ""
                lines.append(
                    f"  {param.name}{option:<20} ({param.type}, {req}){default}"
                )
            elif self.parse_mode == "positional":
                pos = f"[{param.position}]" if param.position is not None else ""
                lines.append(
                    f"  {pos:<5} {param.name:<20} ({param.type}, {req}){default}"
                )
            else:  # mixed
                pos = f"[{param.position}]" if param.position is not None else ""
                option = f" [{param.option}]" if param.option else ""
                lines.append(
                    f"  {pos:<5} {param.name}{option:<20} ({param.type}, {req}){default}"
                )

            if param.description:
                lines.append(f"        {param.description}")
            if param.enum:
                lines.append(f"        Allowed: {', '.join(map(str, param.enum))}")

        return "\n".join(lines)


class SchemaRegistry:
    """Registry for all API schemas loaded from cli_syntax.json."""

    def __init__(self, schema_file: Union[str, Path]):
        """
        Initialize registry from schema file.

        Args:
            schema_file: Path to cli_syntax.json
        """
        self.schema_file = Path(schema_file)
        self._schemas: Dict[str, APISchema] = {}
        self._raw_data: Dict = {}
        self._load_schemas()

    def _load_schemas(self):
        """Load all schemas from JSON file."""
        with open(self.schema_file, encoding="utf-8") as f:
            self._raw_data = json.load(f)

        # Load from new "apis" section if available
        apis_section = self._raw_data.get("apis", {})
        if apis_section:
            for api_name, api_def in apis_section.items():
                self._schemas[api_name] = APISchema.from_dict(api_name, api_def)
        # Fallback to old "api" section for backward compatibility
        else:
            # For now, we'll need to convert old format on the fly
            # This will be populated as we migrate APIs
            pass

    def get_schema(self, api_name: str) -> Optional[APISchema]:
        """
        Get schema for an API.

        Args:
            api_name: API name

        Returns:
            APISchema or None if not found
        """
        return self._schemas.get(api_name)

    def has_schema(self, api_name: str) -> bool:
        """Check if schema exists for API."""
        return api_name in self._schemas

    def register_schema(self, api_name: str, schema_dict: dict):
        """
        Register a new API schema dynamically (for custom APIs).

        This allows custom APIs discovered at runtime to be registered
        so they can be found by get_schema().

        Args:
            api_name: Name of the API
            schema_dict: Schema definition dict

        Example:
            registry.register_schema("extract_hostname", {
                "category": "custom",
                "parse_mode": "options",
                "parameters": {"-var": {...}}
            })
        """
        self._schemas[api_name] = APISchema.from_dict(api_name, schema_dict)
        logger.debug("Registered schema for custom API: %s", api_name)

    def get_help(self, api_name: str) -> str:
        """
        Get help text for an API.

        Args:
            api_name: API name

        Returns:
            Help text or error message
        """
        schema = self.get_schema(api_name)
        return schema.get_help() if schema else f"Unknown API: {api_name}"

    def list_apis(self, category: Optional[str] = None) -> List[str]:
        """
        List all APIs, optionally filtered by category.

        Args:
            category: Optional category filter

        Returns:
            List of API names
        """
        if category:
            return [
                name
                for name, schema in self._schemas.items()
                if schema.category == category
            ]
        return list(self._schemas.keys())

    def validate_all(self) -> List[str]:
        """
        Run consistency checks on all schemas.

        Returns:
            List of error messages (empty if all valid)
        """
        errors = []

        for api_name, schema in self._schemas.items():
            # Check for duplicate positions
            positions = [
                p.position for p in schema.parameters if p.position is not None
            ]
            if len(positions) != len(set(positions)):
                errors.append(
                    f"API '{api_name}' has duplicate parameter positions: {positions}"
                )

            # Check required params have no defaults
            for param in schema.parameters:
                if param.required and param.default is not None:
                    errors.append(
                        f"API '{api_name}' param '{param.name}' is required but has default value"
                    )

        return errors


# Global schema registry instance
# Will be initialized on first import
_schema_registry: Optional[SchemaRegistry] = None


def get_schema_registry() -> SchemaRegistry:
    """Get the global schema registry instance."""
    # pylint: disable=global-statement
    global _schema_registry
    if _schema_registry is None:
        _schema_registry = SchemaRegistry(SYNTAX_DEFINITION_FILEPATH)
    return _schema_registry


def get_schema(api_name: str) -> Optional[APISchema]:
    """Convenience function to get schema for an API."""
    return get_schema_registry().get_schema(api_name)
