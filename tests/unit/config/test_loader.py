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


class TestLoadConfigWithDotEnv:
    """Tests for load_config with .env file loading."""

    def test_loads_env_file_from_config_directory(self, tmp_path: Path) -> None:
        """Load .env file from the same directory as config.yaml."""
        # Create .env file
        env_file = tmp_path / ".env"
        env_file.write_text("DOTENV_TEST_VAR=dotenv-value\n")

        # Create config.yaml that references the environment variable
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
agent:
  system_prompt: ${DOTENV_TEST_VAR}
  llm:
    model_id: "test/model"
""")

        # Ensure the variable is not already set
        with patch.dict(os.environ, {}, clear=True):
            # Clear any existing DOTENV_TEST_VAR
            os.environ.pop("DOTENV_TEST_VAR", None)

            config = load_config(config_file)

        assert config.agent.system_prompt == "dotenv-value"

    def test_no_error_when_env_file_missing(self, tmp_path: Path) -> None:
        """No error when .env file does not exist."""
        # Create config.yaml without .env file
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
agent:
  system_prompt: "Static prompt"
  llm:
    model_id: "test/model"
""")

        # Should not raise any error
        config = load_config(config_file)
        assert config.agent.system_prompt == "Static prompt"

    def test_existing_env_vars_not_overridden(self, tmp_path: Path) -> None:
        """Existing environment variables are not overridden by .env file."""
        # Create .env file with a value
        env_file = tmp_path / ".env"
        env_file.write_text("EXISTING_VAR=dotenv-value\n")

        # Create config.yaml that references the variable
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
agent:
  system_prompt: ${EXISTING_VAR}
  llm:
    model_id: "test/model"
""")

        # Set the existing environment variable
        with patch.dict(os.environ, {"EXISTING_VAR": "original-value"}, clear=False):
            config = load_config(config_file)

        # Should use the original value, not the .env value
        assert config.agent.system_prompt == "original-value"


class TestLoadConfigWithSlackAndDatabase:
    """Tests for load_config with Slack and Database configurations."""

    def test_env_var_expansion_in_slack_config(self, tmp_path: Path) -> None:
        """TC-01-004: Environment variable expansion in slack config."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
agent:
  system_prompt: "Test"
  llm:
    model_id: "test/model"
slack:
  bot_token: ${SLACK_BOT_TOKEN}
  app_token: ${SLACK_APP_TOKEN}
""")

        with patch.dict(
            os.environ,
            {"SLACK_BOT_TOKEN": "xoxb-test", "SLACK_APP_TOKEN": "xapp-test"},
            clear=False,
        ):
            config = load_config(config_file)

        assert config.slack is not None
        assert config.slack.bot_token == "xoxb-test"
        assert config.slack.app_token == "xapp-test"

    def test_config_without_slack_section(self, tmp_path: Path) -> None:
        """TC-01-005: Config without slack section loads successfully."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
agent:
  system_prompt: "Test"
  llm:
    model_id: "test/model"
""")

        config = load_config(config_file)

        assert config.slack is None

    def test_config_without_database_section(self, tmp_path: Path) -> None:
        """TC-01-006: Config without database section loads successfully."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
agent:
  system_prompt: "Test"
  llm:
    model_id: "test/model"
""")

        config = load_config(config_file)

        assert config.database is None

    def test_full_config_with_slack_and_database(self, tmp_path: Path) -> None:
        """TC-01-007: Full config with slack and database sections."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
agent:
  system_prompt: "You are a helpful assistant."
  llm:
    model_id: "anthropic/claude-sonnet-4-20250514"
server:
  host: "127.0.0.1"
  port: 9000
logging:
  level: DEBUG
  format: text
slack:
  bot_token: ${SLACK_BOT_TOKEN}
  app_token: ${SLACK_APP_TOKEN}
  response_delay: 600.0
  response_delay_jitter: 300.0
  context_messages: 50
  thread_messages: 20
database:
  url: "sqlite+aiosqlite:///data/myao3.db"
""")

        with patch.dict(
            os.environ,
            {"SLACK_BOT_TOKEN": "xoxb-test", "SLACK_APP_TOKEN": "xapp-test"},
            clear=False,
        ):
            config = load_config(config_file)

        # Verify all fields are correctly loaded
        assert config.agent.system_prompt == "You are a helpful assistant."
        assert config.agent.llm.model_id == "anthropic/claude-sonnet-4-20250514"
        assert config.server.host == "127.0.0.1"
        assert config.server.port == 9000
        assert config.logging.level == "DEBUG"
        assert config.logging.format == "text"

        # Slack config
        assert config.slack is not None
        assert config.slack.bot_token == "xoxb-test"
        assert config.slack.app_token == "xapp-test"
        assert config.slack.response_delay == 600.0
        assert config.slack.response_delay_jitter == 300.0
        assert config.slack.context_messages == 50
        assert config.slack.thread_messages == 20

        # Database config
        assert config.database is not None
        assert config.database.url == "sqlite+aiosqlite:///data/myao3.db"
