"""
API parameter adapter providing dual access (named and positional).

This module bridges the gap between VMCode parameter tuples and API function
signatures, enabling gradual migration from positional to named access.
"""

from typing import Any, Dict, List, Optional, Tuple, Union


class ApiParams:
    """
    Adapter for API parameters supporting both positional and named access.

    This class enables:
    - Named attribute access: params.rule
    - Dictionary access: params["rule"] or params["-e"]
    - Tuple unpacking: (rule, qaid, ...) = params  (backward compat)
    - Safe get with defaults: params.get("retry_command")
    - Type validation via schema

    Examples:
        >>> # New style (preferred)
        >>> params = ApiParams(data, schema)
        >>> rule = params.rule
        >>> qaid = params.qaid
        >>>
        >>> # Old style (backward compat)
        >>> (rule, qaid, timeout) = params
        >>>
        >>> # Mixed style
        >>> rule = params.rule
        >>> timeout = params.get("timeout", 5)
    """

    def __init__(
        self,
        data: Union[Tuple, List, Dict],
        schema: Optional["APISchema"] = None,  # noqa: F821
    ):
        """
        Initialize parameter adapter.

        Args:
            data: Raw parameters (tuple, list, or dict)
            schema: Optional API schema for validation and conversion
        """
        self._raw = data
        self._schema = schema
        self._data = self._normalize(data, schema)
        self._validated = False

    @classmethod
    def from_tuple(cls, data: Union[Tuple, List]) -> "ApiParams":
        """
        Create from raw tuple without schema validation.

        Args:
            data: Raw parameter tuple

        Returns:
            ApiParams instance
        """
        return cls(data, schema=None)

    def _normalize(
        self,
        data: Union[Tuple, List, Dict],
        schema: Optional["APISchema"],  # noqa: F821
    ) -> Dict[str, Any]:
        """
        Normalize data to dict format.

        Args:
            data: Raw data in various formats
            schema: Optional schema for conversion

        Returns:
            Normalized dict
        """
        if isinstance(data, dict):
            # Already dict - may need alias mapping
            if schema:
                result = {}
                aliases = schema.get_aliases()
                for key, value in data.items():
                    # Map CLI option to parameter name
                    param_name = aliases.get(key, key)
                    result[param_name] = value
                return result
            return data.copy()

        if isinstance(data, (tuple, list)):
            if not schema:
                # No schema - create indexed dict for backward compat
                return {i: val for i, val in enumerate(data)}

            # Use schema to map positions to names
            result = {}
            param_order = schema.get_param_order()

            for i, param_name in enumerate(param_order):
                if i < len(data):
                    result[param_name] = data[i]
                else:
                    # Use default from schema if available
                    param_schema = next(
                        (p for p in schema.parameters if p.name == param_name), None
                    )
                    if param_schema and param_schema.default is not None:
                        result[param_name] = param_schema.default

            return result

        raise TypeError(f"Unsupported data type: {type(data)}")

    def __getattr__(self, name: str) -> Any:
        """
        Named attribute access: params.rule

        Args:
            name: Parameter name

        Returns:
            Parameter value

        Raises:
            AttributeError: If parameter not found
        """
        if name.startswith("_"):
            # Access private attributes normally
            return object.__getattribute__(self, name)

        if name in self._data:
            return self._data[name]

        # Check if it's an indexed access (for backward compat)
        if isinstance(name, int):
            return self._data.get(name)

        raise AttributeError(f"Parameter '{name}' not found")

    def __getitem__(self, key: Union[str, int]) -> Any:
        """
        Dictionary access: params["rule"] or params[0]

        Args:
            key: Parameter name or index

        Returns:
            Parameter value
        """
        return self._data[key]

    def __iter__(self):
        """
        Support tuple unpacking for backward compatibility.

        Yields:
            Parameter values in schema-defined order

        Example:
            >>> (rule, qaid, timeout) = params
        """
        if self._schema:
            # Yield in schema-defined order
            for param_name in self._schema.get_param_order():
                yield self._data.get(param_name)
        else:
            # No schema - yield in order of keys (for indexed dict) or values
            if all(isinstance(k, int) for k in self._data.keys()):
                # Indexed dict - yield in order
                for i in sorted(self._data.keys()):
                    yield self._data[i]
            else:
                # Named dict - yield values
                yield from self._data.values()

    def __len__(self) -> int:
        """Return number of parameters."""
        return len(self._data)

    def __contains__(self, key: str) -> bool:
        """Check if parameter exists."""
        return key in self._data

    def get(self, key: str, default: Any = None) -> Any:
        """
        Safe access with default value.

        Args:
            key: Parameter name
            default: Default value if not found

        Returns:
            Parameter value or default
        """
        return self._data.get(key, default)

    def keys(self):
        """Get all parameter names."""
        return self._data.keys()

    def values(self):
        """Get all parameter values."""
        return self._data.values()

    def items(self):
        """Get all (name, value) pairs."""
        return self._data.items()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to plain dict.

        Returns:
            Dict of all parameters
        """
        return self._data.copy()

    def validate(self) -> None:
        """
        Validate parameters against schema.

        Raises:
            ValueError: If validation fails
        """
        if not self._schema or self._validated:
            return

        # Validate each parameter
        validated_data = self._schema.validate_params(self._data)
        self._data = validated_data
        self._validated = True

    def __repr__(self) -> str:
        """String representation for debugging."""
        schema_info = f" (schema: {self._schema.name})" if self._schema else ""
        return f"ApiParams({self._data}{schema_info})"

    def __str__(self) -> str:
        """User-friendly string representation."""
        if self._schema:
            return f"Params for {self._schema.name}: {self._data}"
        return f"Params: {self._data}"
