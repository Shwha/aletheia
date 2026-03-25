"""
Tests for configuration loading and validation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aletheia.config import AletheiaSettings, load_suite


class TestAletheiaSettings:
    """Tests for environment-based settings."""

    def test_default_settings(self) -> None:
        """Settings should load with defaults even without .env file."""
        settings = AletheiaSettings(
            _env_file=None,  # type: ignore[call-arg]
        )
        assert settings.verify_tls is True
        assert settings.log_level == "INFO"

    def test_api_keys_are_secret(self) -> None:
        """API keys must never appear in repr or string conversion."""
        settings = AletheiaSettings(
            _env_file=None,  # type: ignore[call-arg]
        )
        repr_str = repr(settings)
        assert "sk-" not in repr_str


class TestSuiteLoading:
    """Tests for YAML suite loading."""

    def test_load_quick_suite(self) -> None:
        """The quick suite should be loadable from the suites/ directory."""
        suites_dir = Path(__file__).resolve().parent.parent / "suites"
        suite = load_suite("quick", suites_dir)
        assert suite.name == "quick"
        assert len(suite.dimensions) == 7
        assert suite.timeout_per_probe_seconds == 30

    def test_missing_suite_raises(self) -> None:
        with pytest.raises(FileNotFoundError, match="not found"):
            load_suite("nonexistent_suite", Path("/tmp"))
