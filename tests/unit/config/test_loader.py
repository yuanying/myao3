"""Tests for config loader."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from myao3.config.loader import (
    ConfigFileNotFoundError,
    ConfigParseError,
    EnvVarNotFoundError,
    expand_env_vars,
    load_config,
    parse_cli_args,
)
from myao3.config.models import AppConfig


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_valid_config(self, tmp_path: Path) -> None:
        """TC-02-001: Load a valid config file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
agent:
  system_prompt: "You are a helpful assistant."
  llm:
    model_id: "anthropic/claude-sonnet-4-20250514"
server:
  port: 9000
""")

        config = load_config(config_file)

        assert isinstance(config, AppConfig)
        assert config.agent.system_prompt == "You are a helpful assistant."
        assert config.agent.llm.model_id == "anthropic/claude-sonnet-4-20250514"
        assert config.server.port == 9000
        assert config.server.host == "0.0.0.0"

    def test_file_not_found(self) -> None:
        """TC-02-006: File not found raises ConfigFileNotFoundError."""
        with pytest.raises(ConfigFileNotFoundError) as exc_info:
            load_config(Path("/nonexistent/path/config.yaml"))

        assert "not found" in str(exc_info.value).lower()

    def test_invalid_yaml(self, tmp_path: Path) -> None:
        """TC-02-005: Invalid YAML format raises ConfigParseError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: format:")

        with pytest.raises(ConfigParseError):
            load_config(config_file)

    def test_missing_required_field(self, tmp_path: Path) -> None:
        """TC-02-004: Missing required field raises ValidationError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
server:
  port: 8080
""")

        with pytest.raises(ValidationError) as exc_info:
            load_config(config_file)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("agent",) for e in errors)


class TestExpandEnvVars:
    """Tests for expand_env_vars function."""

    def test_expand_string_env_var(self) -> None:
        """TC-02-002: Expand environment variable in string."""
        with patch.dict(os.environ, {"API_KEY": "test-key"}, clear=False):
            result = expand_env_vars("${API_KEY}")

        assert result == "test-key"

    def test_expand_nested_dict(self) -> None:
        """TC-02-002: Expand environment variable in nested dict."""
        with patch.dict(os.environ, {"API_KEY": "test-key"}, clear=False):
            data = {
                "agent": {
                    "llm": {
                        "client_args": {
                            "api_key": "${API_KEY}",
                        }
                    }
                }
            }
            result = expand_env_vars(data)

        assert result["agent"]["llm"]["client_args"]["api_key"] == "test-key"

    def test_expand_in_list(self) -> None:
        """Expand environment variable in list."""
        with patch.dict(os.environ, {"VAR1": "value1", "VAR2": "value2"}, clear=False):
            data = ["${VAR1}", "${VAR2}", "static"]
            result = expand_env_vars(data)

        assert result == ["value1", "value2", "static"]

    def test_no_expansion_for_partial_match(self) -> None:
        """No expansion for partial match (prefix/suffix present)."""
        with patch.dict(os.environ, {"VAR": "value"}, clear=False):
            result = expand_env_vars("prefix${VAR}suffix")

        # Partial match should not be expanded
        assert result == "prefix${VAR}suffix"

    def test_undefined_env_var_raises_error(self) -> None:
        """TC-02-003: Undefined environment variable raises EnvVarNotFoundError."""
        # Ensure the variable is not set
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(EnvVarNotFoundError) as exc_info:
                expand_env_vars("${UNDEFINED_VAR}")

            assert "UNDEFINED_VAR" in str(exc_info.value)

    def test_non_string_values_unchanged(self) -> None:
        """Non-string values should pass through unchanged."""
        data = {
            "port": 8080,
            "enabled": True,
            "ratio": 0.5,
            "nothing": None,
        }
        result = expand_env_vars(data)

        assert result == data


class TestLoadConfigWithEnvVars:
    """Tests for load_config with environment variable expansion."""

    def test_load_config_with_env_vars(self, tmp_path: Path) -> None:
        """TC-02-002: Load config with environment variable expansion."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
agent:
  system_prompt: "Test"
  llm:
    model_id: "test/model"
    client_args:
      api_key: ${API_KEY}
""")

        with patch.dict(os.environ, {"API_KEY": "test-key"}, clear=False):
            config = load_config(config_file)

        assert config.agent.llm.client_args["api_key"] == "test-key"

    def test_load_config_undefined_env_var(self, tmp_path: Path) -> None:
        """TC-02-003: Undefined environment variable raises error."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
agent:
  system_prompt: ${UNDEFINED_VAR}
  llm:
    model_id: "test/model"
""")

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(EnvVarNotFoundError) as exc_info:
                load_config(config_file)

            assert "UNDEFINED_VAR" in str(exc_info.value)


class TestParseCliArgs:
    """Tests for CLI argument parsing."""

    def test_parse_config_long_option(self) -> None:
        """TC-02-007: Parse --config argument."""
        args = ["--config", "config.yaml"]
        result = parse_cli_args(args)

        assert result == Path("config.yaml")

    def test_parse_config_short_option(self) -> None:
        """TC-02-007: Parse -c argument."""
        args = ["-c", "/path/to/config.yaml"]
        result = parse_cli_args(args)

        assert result == Path("/path/to/config.yaml")

    def test_default_config_path(self) -> None:
        """TC-02-008: Default config path is config.yaml."""
        args: list[str] = []
        result = parse_cli_args(args)

        assert result == Path("config.yaml")
