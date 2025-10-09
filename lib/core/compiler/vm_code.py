# pylint: disable=import-outside-toplevel


class VMCode:
    def __init__(self, line_number, operation, parameters, schema=None):
        self.line_number = line_number
        self.operation = operation
        self.parameters = parameters
        self._schema = schema  # Optional schema reference

    def __str__(self):
        parameters = " ".join(str(p) for p in self.parameters)
        operation = f"{self.line_number} {self.operation}"

        return operation + (f" {parameters}" if parameters else "")

    def add_parameter(self, parameter):
        self.parameters = (*self.parameters, parameter)

    def __repr__(self):
        parameters = " ".join(str(p) for p in self.parameters)
        operation = f"{self.line_number} {self.operation}"

        return operation + (f" {parameters}" if parameters else "")

    def get_schema(self):
        """
        Get schema for this operation.

        Returns:
            APISchema or None if not found
        """
        if self._schema:
            return self._schema

        # Lazy load schema on demand
        try:
            from .schema_loader import get_schema

            self._schema = get_schema(self.operation)
            return self._schema
        except ImportError:
            return None

    def as_params(self):
        """
        Convert parameters to ApiParams object for modern API access.

        Returns:
            ApiParams instance with schema validation
        """
        from lib.core.executor.api_params import ApiParams

        schema = self.get_schema()
        return ApiParams(self.parameters, schema)
