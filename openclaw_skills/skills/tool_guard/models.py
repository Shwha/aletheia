"""ToolGuard-specific models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ParameterSchema(BaseModel):
    """Schema for a single tool parameter."""

    type: str = "string"  # string, integer, float, boolean, path, enum
    required: bool = True
    description: str = ""
    default: Any = None
    enum_values: list[str] | None = None
    min_value: float | None = None
    max_value: float | None = None
    pattern: str | None = None  # regex pattern for string validation


class ToolSchema(BaseModel):
    """Schema for a registered tool."""

    name: str
    description: str = ""
    parameters: dict[str, ParameterSchema] = Field(default_factory=dict)
    destructive: bool = False
    requires_confirmation: bool = False
    max_calls_per_minute: int | None = None


class ValidationResult(BaseModel):
    """Result of validating a tool call."""

    valid: bool = True
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    is_destructive: bool = False
