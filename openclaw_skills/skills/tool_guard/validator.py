"""Tool call validation — the unconcealment layer.

Every tool call is validated against its schema before execution.
This is transparency made structural: the system cannot act without
showing its work.
"""

from __future__ import annotations

import re
from typing import Any

from openclaw_skills.models import ToolCallRequest
from openclaw_skills.skills.tool_guard.models import (
    ParameterSchema,
    ToolSchema,
    ValidationResult,
)


class ToolGuardValidator:
    """Validates tool calls against registered schemas."""

    def __init__(self) -> None:
        self._schemas: dict[str, ToolSchema] = {}

    def register_schema(self, schema: ToolSchema) -> None:
        """Register a tool schema for validation."""
        self._schemas[schema.name] = schema

    def register_schemas(self, schemas: list[ToolSchema]) -> None:
        """Register multiple tool schemas."""
        for schema in schemas:
            self.register_schema(schema)

    def is_registered(self, tool_name: str) -> bool:
        """Check if a tool has a registered schema."""
        return tool_name in self._schemas

    def validate(self, call: ToolCallRequest, strict: bool = False) -> ValidationResult:
        """Validate a tool call against its schema.

        Args:
            call: The tool call to validate.
            strict: If True, reject unregistered tools.

        Returns:
            ValidationResult with valid/invalid status and error details.
        """
        errors: list[str] = []
        warnings: list[str] = []
        is_destructive = False

        schema = self._schemas.get(call.tool_name)

        if schema is None:
            if strict:
                errors.append(f"Unregistered tool: {call.tool_name}")
                return ValidationResult(valid=False, errors=errors)
            warnings.append(f"No schema registered for tool: {call.tool_name}")
            return ValidationResult(valid=True, warnings=warnings)

        is_destructive = schema.destructive

        # Check required parameters
        for param_name, param_schema in schema.parameters.items():
            if param_schema.required and param_name not in call.parameters:
                if param_schema.default is None:
                    errors.append(f"Missing required parameter: {param_name}")

        # Validate provided parameters
        for param_name, value in call.parameters.items():
            param_schema = schema.parameters.get(param_name)
            if param_schema is None:
                warnings.append(f"Unknown parameter: {param_name}")
                continue

            param_errors = _validate_parameter(param_name, value, param_schema)
            errors.extend(param_errors)

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            is_destructive=is_destructive,
        )

    def is_destructive(self, tool_name: str) -> bool:
        """Check if a tool is marked as destructive."""
        schema = self._schemas.get(tool_name)
        return schema.destructive if schema else False


def _validate_parameter(
    name: str,
    value: Any,
    schema: ParameterSchema,
) -> list[str]:
    """Validate a single parameter against its schema."""
    errors: list[str] = []

    # Type checking
    expected_types: dict[str, tuple[type, ...]] = {
        "string": (str,),
        "integer": (int,),
        "float": (int, float),
        "boolean": (bool,),
        "path": (str,),
        "enum": (str,),
    }

    valid_types = expected_types.get(schema.type)
    if valid_types and not isinstance(value, valid_types):
        errors.append(
            f"Parameter '{name}': expected {schema.type}, got {type(value).__name__}"
        )
        return errors  # Can't validate further with wrong type

    # Enum validation
    if schema.enum_values is not None and value not in schema.enum_values:
        errors.append(
            f"Parameter '{name}': value '{value}' not in allowed values: {schema.enum_values}"
        )

    # Numeric range validation
    if isinstance(value, (int, float)):
        if schema.min_value is not None and value < schema.min_value:
            errors.append(f"Parameter '{name}': {value} < minimum {schema.min_value}")
        if schema.max_value is not None and value > schema.max_value:
            errors.append(f"Parameter '{name}': {value} > maximum {schema.max_value}")

    # Pattern validation
    if schema.pattern and isinstance(value, str):
        if not re.search(schema.pattern, value):
            errors.append(
                f"Parameter '{name}': value doesn't match pattern '{schema.pattern}'"
            )

    return errors
