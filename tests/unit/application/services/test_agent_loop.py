"""Tests for AgentLoop class."""

import pytest
import structlog

from myao3.application.services.agent_loop import AgentLoop
from myao3.config.models import AgentConfig, LLMConfig, LoggingConfig
from myao3.domain.entities.event import PingEvent
from myao3.infrastructure.logging.setup import setup_logging


@pytest.fixture
def mock_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set MOCK_LLM=true environment variable."""
    monkeypatch.setenv("MOCK_LLM", "true")


@pytest.fixture
def agent_config() -> AgentConfig:
    """Create a test AgentConfig."""
    return AgentConfig(
        system_prompt="You are a helpful test assistant.",
        llm=LLMConfig(model_id="anthropic/claude-sonnet-4-20250514"),
    )


@pytest.fixture
def logger() -> structlog.stdlib.BoundLogger:
    """Create a test logger."""
    setup_logging(LoggingConfig(level="DEBUG", format="json"))
    return structlog.stdlib.get_logger("test")


class TestAgentLoopInitialization:
    """Tests for AgentLoop initialization."""

    def test_initialization_succeeds(
        self,
        mock_llm_env: None,
        agent_config: AgentConfig,
        logger: structlog.stdlib.BoundLogger,
    ) -> None:
        """TC-06-001: AgentLoop initializes without error."""
        agent_loop = AgentLoop(config=agent_config, logger=logger)

        assert agent_loop is not None

    def test_system_prompt_is_configured(
        self,
        mock_llm_env: None,
        agent_config: AgentConfig,
        logger: structlog.stdlib.BoundLogger,
    ) -> None:
        """TC-06-005: system_prompt is set from config."""
        agent_loop = AgentLoop(config=agent_config, logger=logger)

        assert agent_loop._system_prompt == agent_config.system_prompt


class TestAgentLoopProcess:
    """Tests for AgentLoop.process() method."""

    @pytest.mark.asyncio
    async def test_process_ping_event_succeeds(
        self,
        mock_llm_env: None,
        agent_config: AgentConfig,
        logger: structlog.stdlib.BoundLogger,
    ) -> None:
        """TC-06-002: AgentLoop.process() completes without error for PingEvent."""
        agent_loop = AgentLoop(config=agent_config, logger=logger)
        event = PingEvent()

        await agent_loop.process(event)

    @pytest.mark.asyncio
    async def test_process_returns_mock_response(
        self,
        mock_llm_env: None,
        agent_config: AgentConfig,
        logger: structlog.stdlib.BoundLogger,
    ) -> None:
        """TC-06-004: AgentLoop returns mock LLM response when MOCK_LLM=true."""
        agent_loop = AgentLoop(config=agent_config, logger=logger)
        event = PingEvent()

        result = await agent_loop.process(event)

        assert result is not None
        assert "Mock LLM response" in result


class TestAgentLoopLogging:
    """Tests for AgentLoop logging behavior."""

    @pytest.mark.asyncio
    async def test_logs_event_processing_start(
        self,
        mock_llm_env: None,
        agent_config: AgentConfig,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """TC-06-006: AgentLoop logs event processing start."""
        setup_logging(LoggingConfig(level="DEBUG", format="json"))
        logger = structlog.stdlib.get_logger("test")
        agent_loop = AgentLoop(config=agent_config, logger=logger)
        event = PingEvent()

        await agent_loop.process(event)

        captured = capsys.readouterr()
        assert "event_id" in captured.out or event.id in captured.out

    @pytest.mark.asyncio
    async def test_logs_event_processing_complete(
        self,
        mock_llm_env: None,
        agent_config: AgentConfig,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """TC-06-006: AgentLoop logs event processing completion."""
        setup_logging(LoggingConfig(level="DEBUG", format="json"))
        logger = structlog.stdlib.get_logger("test")
        agent_loop = AgentLoop(config=agent_config, logger=logger)
        event = PingEvent()

        await agent_loop.process(event)

        captured = capsys.readouterr()
        lines = [line for line in captured.out.strip().split("\n") if line]
        assert len(lines) >= 2


class TestAgentLoopExceptionHandling:
    """Tests for AgentLoop exception handling."""

    @pytest.mark.asyncio
    async def test_exception_is_logged_and_propagated(
        self,
        monkeypatch: pytest.MonkeyPatch,
        agent_config: AgentConfig,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """TC-06-007: Exception is logged and propagated."""
        monkeypatch.setenv("MOCK_LLM", "error")
        setup_logging(LoggingConfig(level="DEBUG", format="json"))
        logger = structlog.stdlib.get_logger("test")
        agent_loop = AgentLoop(config=agent_config, logger=logger)
        event = PingEvent()

        with pytest.raises(Exception):
            await agent_loop.process(event)

        captured = capsys.readouterr()
        log_lines = captured.out.strip().split("\n")
        has_error_log = any("error" in line.lower() for line in log_lines)
        assert has_error_log
