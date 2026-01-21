"""Unit tests for __main__.py entry point."""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from myao3.config import AppConfig


class TestParseArgs:
    """Test cases for parse_args function."""

    def test_default_config_path(self) -> None:
        """TC-07-008: Default config path should be config.yaml."""
        from myao3.__main__ import parse_args

        args = parse_args([])
        assert args.config == Path("config.yaml")

    def test_config_path_with_short_option(self) -> None:
        """Config can be specified with -c option."""
        from myao3.__main__ import parse_args

        args = parse_args(["-c", "custom.yaml"])
        assert args.config == Path("custom.yaml")

    def test_config_path_with_long_option(self) -> None:
        """Config can be specified with --config option."""
        from myao3.__main__ import parse_args

        args = parse_args(["--config", "custom.yaml"])
        assert args.config == Path("custom.yaml")


class TestMainWithConfigErrors:
    """Test cases for main function with configuration errors."""

    def test_config_file_not_found(self, capsys: pytest.CaptureFixture[str]) -> None:
        """TC-07-002: Non-existent config file should cause exit with error."""
        from myao3.__main__ import main

        with patch.object(sys, "argv", ["myao3", "-c", "nonexistent.yaml"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "nonexistent.yaml" in captured.err
            assert "not found" in captured.err

    def test_invalid_config_file(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """TC-07-003: Invalid config file should cause exit with error."""
        from myao3.__main__ import main

        # Create invalid YAML file
        invalid_config = tmp_path / "invalid.yaml"
        invalid_config.write_text("invalid: yaml: content:")

        with patch.object(sys, "argv", ["myao3", "-c", str(invalid_config)]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Error" in captured.err


class TestMainAsync:
    """Test cases for main_async function."""

    @pytest.fixture
    def mock_config(self) -> AppConfig:
        """Create a mock AppConfig."""
        from myao3.config import (
            AgentConfig,
            AppConfig,
            LLMConfig,
            LoggingConfig,
            ServerConfig,
        )

        return AppConfig(
            agent=AgentConfig(
                system_prompt="Test prompt",
                llm=LLMConfig(model_id="test-model"),
            ),
            server=ServerConfig(host="127.0.0.1", port=0),
            logging=LoggingConfig(level="INFO", format="text"),
        )

    @pytest.mark.asyncio
    async def test_normal_startup_and_shutdown(self, mock_config: AppConfig) -> None:
        """TC-07-001: Normal startup and shutdown."""
        from myao3.__main__ import main_async

        with (
            patch("myao3.__main__.load_config", return_value=mock_config),
            patch("myao3.__main__.setup_logging") as mock_setup_logging,
            patch("myao3.__main__.HTTPServer") as mock_server_class,
            patch("myao3.__main__.AgentLoop") as mock_agent_loop_class,
            patch("myao3.__main__.EventQueue") as mock_event_queue_class,
        ):
            mock_server = AsyncMock()
            mock_server_class.return_value = mock_server

            mock_agent_loop = MagicMock()
            mock_agent_loop.process = AsyncMock()
            mock_agent_loop_class.return_value = mock_agent_loop

            mock_event_queue = MagicMock()
            # Make dequeue wait until cancelled
            mock_event_queue.dequeue = AsyncMock(side_effect=asyncio.CancelledError)
            mock_event_queue_class.return_value = mock_event_queue

            # Run main_async with immediate shutdown
            async def run_with_shutdown() -> int:
                task = asyncio.create_task(main_async(Path("config.yaml")))
                # Give time for startup
                await asyncio.sleep(0.05)
                # Cancel the task to simulate shutdown
                task.cancel()
                try:
                    return await task
                except asyncio.CancelledError:
                    return 0

            exit_code = await run_with_shutdown()

            assert exit_code == 0
            mock_setup_logging.assert_called_once_with(mock_config.logging)
            mock_server.start.assert_called_once()
            mock_server.stop.assert_called_once()


class TestRunMainLoop:
    """Test cases for run_main_loop function."""

    @pytest.mark.asyncio
    async def test_processes_events_until_shutdown(self) -> None:
        """TC-07-004/005: Process events until shutdown signal."""
        from myao3.__main__ import run_main_loop

        mock_logger = MagicMock()
        shutdown_event = asyncio.Event()

        # Create mock event
        mock_event = MagicMock()
        mock_event.id = "test-event-1"

        # Create mock event queue that returns one event then blocks
        mock_event_queue = MagicMock()
        dequeue_call_count = 0

        async def mock_dequeue() -> MagicMock:
            nonlocal dequeue_call_count
            dequeue_call_count += 1
            if dequeue_call_count == 1:
                return mock_event
            # After first event, wait for shutdown
            await asyncio.sleep(10)
            return mock_event

        mock_event_queue.dequeue = mock_dequeue
        mock_event_queue.mark_done = MagicMock()

        mock_agent_loop = MagicMock()
        mock_agent_loop.process = AsyncMock()

        running = True

        def is_running() -> bool:
            return running

        async def run_test() -> None:
            nonlocal running
            loop_task = asyncio.create_task(
                run_main_loop(
                    event_queue=mock_event_queue,
                    agent_loop=mock_agent_loop,
                    shutdown_event=shutdown_event,
                    running_check=is_running,
                    logger=mock_logger,
                )
            )

            # Wait for event to be processed
            await asyncio.sleep(0.05)

            # Trigger shutdown
            running = False
            shutdown_event.set()

            await asyncio.wait_for(loop_task, timeout=1.0)

        await run_test()

        mock_agent_loop.process.assert_called_once_with(mock_event)
        mock_event_queue.mark_done.assert_called_once_with(mock_event)

    @pytest.mark.asyncio
    async def test_event_processing_during_shutdown(self) -> None:
        """TC-07-006: Event being processed when shutdown occurs."""
        from myao3.__main__ import run_main_loop

        mock_logger = MagicMock()
        shutdown_event = asyncio.Event()

        mock_event = MagicMock()
        mock_event.id = "test-event-1"

        mock_event_queue = MagicMock()
        event_returned = asyncio.Event()

        async def mock_dequeue() -> MagicMock:
            event_returned.set()
            return mock_event

        mock_event_queue.dequeue = mock_dequeue
        mock_event_queue.mark_done = MagicMock()

        mock_agent_loop = MagicMock()
        processing_started = asyncio.Event()
        processing_should_complete = asyncio.Event()

        async def slow_process(event: MagicMock) -> None:
            processing_started.set()
            await processing_should_complete.wait()

        mock_agent_loop.process = slow_process

        running = True

        def is_running() -> bool:
            return running

        async def run_test() -> None:
            nonlocal running
            loop_task = asyncio.create_task(
                run_main_loop(
                    event_queue=mock_event_queue,
                    agent_loop=mock_agent_loop,
                    shutdown_event=shutdown_event,
                    running_check=is_running,
                    logger=mock_logger,
                )
            )

            # Wait for processing to start
            await processing_started.wait()

            # Trigger shutdown while processing
            running = False
            shutdown_event.set()

            # Allow processing to complete
            processing_should_complete.set()

            await asyncio.wait_for(loop_task, timeout=1.0)

        await run_test()

        # mark_done should be called even after shutdown signal
        mock_event_queue.mark_done.assert_called_once_with(mock_event)

    @pytest.mark.asyncio
    async def test_exception_during_event_processing(self) -> None:
        """Event processing exception should be logged and continue."""
        from myao3.__main__ import run_main_loop

        mock_logger = MagicMock()
        shutdown_event = asyncio.Event()

        mock_event = MagicMock()
        mock_event.id = "test-event-1"

        mock_event_queue = MagicMock()
        dequeue_call_count = 0

        async def mock_dequeue() -> MagicMock:
            nonlocal dequeue_call_count
            dequeue_call_count += 1
            if dequeue_call_count == 1:
                return mock_event
            await asyncio.sleep(10)
            return mock_event

        mock_event_queue.dequeue = mock_dequeue
        mock_event_queue.mark_done = MagicMock()

        mock_agent_loop = MagicMock()
        mock_agent_loop.process = AsyncMock(side_effect=Exception("Test error"))

        running = True

        def is_running() -> bool:
            return running

        async def run_test() -> None:
            nonlocal running
            loop_task = asyncio.create_task(
                run_main_loop(
                    event_queue=mock_event_queue,
                    agent_loop=mock_agent_loop,
                    shutdown_event=shutdown_event,
                    running_check=is_running,
                    logger=mock_logger,
                )
            )

            await asyncio.sleep(0.05)
            running = False
            shutdown_event.set()

            await asyncio.wait_for(loop_task, timeout=1.0)

        await run_test()

        # mark_done should still be called after exception
        mock_event_queue.mark_done.assert_called_once_with(mock_event)
        # Error should be logged
        mock_logger.error.assert_called()


class TestShutdownTimeout:
    """Test cases for shutdown timeout."""

    @pytest.fixture
    def mock_config(self) -> AppConfig:
        """Create a mock AppConfig."""
        from myao3.config import (
            AgentConfig,
            AppConfig,
            LLMConfig,
            LoggingConfig,
            ServerConfig,
        )

        return AppConfig(
            agent=AgentConfig(
                system_prompt="Test prompt",
                llm=LLMConfig(model_id="test-model"),
            ),
            server=ServerConfig(host="127.0.0.1", port=0),
            logging=LoggingConfig(level="INFO", format="text"),
        )

    def test_shutdown_timeout_constant(self) -> None:
        """SHUTDOWN_TIMEOUT constant is defined as 30 seconds."""
        from myao3.__main__ import SHUTDOWN_TIMEOUT

        assert SHUTDOWN_TIMEOUT == 30

    @pytest.mark.asyncio
    async def test_shutdown_completes_within_timeout(
        self, mock_config: AppConfig
    ) -> None:
        """Shutdown completes within timeout."""
        from myao3.__main__ import main_async

        with (
            patch("myao3.__main__.load_config", return_value=mock_config),
            patch("myao3.__main__.setup_logging"),
            patch("myao3.__main__.HTTPServer") as mock_server_class,
            patch("myao3.__main__.AgentLoop") as mock_agent_loop_class,
            patch("myao3.__main__.EventQueue") as mock_event_queue_class,
        ):
            mock_server = AsyncMock()
            # stop() completes immediately
            mock_server.stop = AsyncMock()
            mock_server_class.return_value = mock_server

            mock_agent_loop = MagicMock()
            mock_agent_loop.process = AsyncMock()
            mock_agent_loop_class.return_value = mock_agent_loop

            mock_event_queue = MagicMock()
            mock_event_queue.dequeue = AsyncMock(side_effect=asyncio.CancelledError)
            mock_event_queue_class.return_value = mock_event_queue

            async def run_with_shutdown() -> int:
                task = asyncio.create_task(
                    main_async(Path("config.yaml"), shutdown_timeout=0.5)
                )
                await asyncio.sleep(0.05)
                task.cancel()
                try:
                    return await task
                except asyncio.CancelledError:
                    return 0

            exit_code = await run_with_shutdown()

            assert exit_code == 0
            mock_server.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_timeout_forces_termination(
        self, mock_config: AppConfig
    ) -> None:
        """TC-07-007: Shutdown timeout forces termination with warning log."""
        import os
        import signal as signal_module

        from myao3.__main__ import main_async

        with (
            patch("myao3.__main__.load_config", return_value=mock_config),
            patch("myao3.__main__.setup_logging"),
            patch("myao3.__main__.HTTPServer") as mock_server_class,
            patch("myao3.__main__.AgentLoop") as mock_agent_loop_class,
            patch("myao3.__main__.EventQueue") as mock_event_queue_class,
            patch("myao3.__main__.get_logger") as mock_get_logger,
        ):
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            mock_server = AsyncMock()

            # stop() hangs for 10 seconds (longer than timeout)
            async def slow_stop() -> None:
                await asyncio.sleep(10)

            mock_server.stop = slow_stop
            mock_server_class.return_value = mock_server

            mock_agent_loop = MagicMock()
            mock_agent_loop.process = AsyncMock()
            mock_agent_loop_class.return_value = mock_agent_loop

            mock_event_queue = MagicMock()

            # Make dequeue block until cancelled
            async def blocking_dequeue() -> MagicMock:
                await asyncio.sleep(100)
                return MagicMock()

            mock_event_queue.dequeue = blocking_dequeue
            mock_event_queue_class.return_value = mock_event_queue

            async def run_with_shutdown() -> int:
                task = asyncio.create_task(
                    main_async(Path("config.yaml"), shutdown_timeout=0.1)
                )
                await asyncio.sleep(0.05)  # Give time for startup
                # Send SIGTERM to trigger shutdown handler
                os.kill(os.getpid(), signal_module.SIGTERM)
                return await asyncio.wait_for(task, timeout=5.0)

            exit_code = await run_with_shutdown()

            # Exit code should still be 0 (shutdown delay is not a fatal error)
            assert exit_code == 0
            # Warning log should be output
            mock_logger.warning.assert_called()
            # Check that warning was called with timeout message
            warning_calls = mock_logger.warning.call_args_list
            timeout_warning_found = any(
                "timed out" in str(call).lower() or "timeout" in str(call).lower()
                for call in warning_calls
            )
            assert timeout_warning_found, (
                f"Expected timeout warning, got: {warning_calls}"
            )
