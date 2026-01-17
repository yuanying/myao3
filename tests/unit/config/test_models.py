"""Tests for config Pydantic models."""

import pytest
from pydantic import ValidationError

from myao3.config.models import (
    AgentConfig,
    AppConfig,
    LLMConfig,
    LoggingConfig,
    ServerConfig,
)


class TestLLMConfig:
    """Tests for LLMConfig model."""

    def test_minimal_config(self) -> None:
        """LLMConfig with only required field model_id."""
        config = LLMConfig(model_id="anthropic/claude-sonnet-4-20250514")

        assert config.model_id == "anthropic/claude-sonnet-4-20250514"
        assert config.params == {}
        assert config.client_args == {}

    def test_full_config(self) -> None:
        """LLMConfig with all fields."""
        config = LLMConfig(
            model_id="openai/gpt-4",
            params={"temperature": 0.7, "max_tokens": 1000},
            client_args={"api_key": "test-key", "base_url": "https://api.example.com"},
        )

        assert config.model_id == "openai/gpt-4"
        assert config.params == {"temperature": 0.7, "max_tokens": 1000}
        assert config.client_args == {
            "api_key": "test-key",
            "base_url": "https://api.example.com",
        }

    def test_missing_model_id_raises_error(self) -> None:
        """LLMConfig without model_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            LLMConfig()  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("model_id",)
        assert errors[0]["type"] == "missing"


class TestAgentConfig:
    """Tests for AgentConfig model."""

    def test_minimal_config(self) -> None:
        """AgentConfig with required fields."""
        config = AgentConfig(
            system_prompt="You are a helpful assistant.",
            llm=LLMConfig(model_id="anthropic/claude-sonnet-4-20250514"),
        )

        assert config.system_prompt == "You are a helpful assistant."
        assert config.llm.model_id == "anthropic/claude-sonnet-4-20250514"

    def test_missing_system_prompt_raises_error(self) -> None:
        """AgentConfig without system_prompt raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AgentConfig(llm=LLMConfig(model_id="test/model"))  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("system_prompt",) for e in errors)

    def test_missing_llm_raises_error(self) -> None:
        """AgentConfig without llm raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AgentConfig(system_prompt="Test")  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("llm",) for e in errors)


class TestServerConfig:
    """Tests for ServerConfig model."""

    def test_default_values(self) -> None:
        """ServerConfig has correct default values."""
        config = ServerConfig()

        assert config.host == "0.0.0.0"
        assert config.port == 8080

    def test_custom_values(self) -> None:
        """ServerConfig with custom values."""
        config = ServerConfig(host="127.0.0.1", port=9000)

        assert config.host == "127.0.0.1"
        assert config.port == 9000


class TestLoggingConfig:
    """Tests for LoggingConfig model."""

    def test_default_values(self) -> None:
        """LoggingConfig has correct default values."""
        config = LoggingConfig()

        assert config.level == "INFO"
        assert config.format == "json"

    def test_custom_values(self) -> None:
        """LoggingConfig with custom values."""
        config = LoggingConfig(level="DEBUG", format="text")

        assert config.level == "DEBUG"
        assert config.format == "text"

    def test_invalid_level_raises_error(self) -> None:
        """LoggingConfig with invalid level raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            LoggingConfig(level="INVALID")  # type: ignore[arg-type]

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("level",) for e in errors)

    def test_invalid_format_raises_error(self) -> None:
        """LoggingConfig with invalid format raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            LoggingConfig(format="invalid")  # type: ignore[arg-type]

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("format",) for e in errors)

    def test_all_valid_levels(self) -> None:
        """LoggingConfig accepts all valid log levels."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in valid_levels:
            config = LoggingConfig(level=level)  # type: ignore[arg-type]
            assert config.level == level


class TestAppConfig:
    """Tests for AppConfig model."""

    def test_minimal_config(self) -> None:
        """AppConfig with only required fields."""
        config = AppConfig(
            agent=AgentConfig(
                system_prompt="You are a helpful assistant.",
                llm=LLMConfig(model_id="anthropic/claude-sonnet-4-20250514"),
            )
        )

        assert config.agent.system_prompt == "You are a helpful assistant."
        assert config.agent.llm.model_id == "anthropic/claude-sonnet-4-20250514"
        assert config.server.host == "0.0.0.0"
        assert config.server.port == 8080
        assert config.logging.level == "INFO"
        assert config.logging.format == "json"

    def test_full_config(self) -> None:
        """AppConfig with all fields."""
        config = AppConfig(
            agent=AgentConfig(
                system_prompt="You are a helpful assistant.",
                llm=LLMConfig(
                    model_id="anthropic/claude-sonnet-4-20250514",
                    params={"temperature": 0.5},
                ),
            ),
            server=ServerConfig(host="127.0.0.1", port=9000),
            logging=LoggingConfig(level="DEBUG", format="text"),
        )

        assert config.agent.system_prompt == "You are a helpful assistant."
        assert config.agent.llm.model_id == "anthropic/claude-sonnet-4-20250514"
        assert config.agent.llm.params == {"temperature": 0.5}
        assert config.server.host == "127.0.0.1"
        assert config.server.port == 9000
        assert config.logging.level == "DEBUG"
        assert config.logging.format == "text"

    def test_missing_agent_raises_error(self) -> None:
        """AppConfig without agent raises ValidationError (TC-02-004)."""
        with pytest.raises(ValidationError) as exc_info:
            AppConfig()  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("agent",) for e in errors)
        assert any(e["type"] == "missing" for e in errors)
