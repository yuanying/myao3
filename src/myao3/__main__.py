"""Application entry point for myao3."""

import argparse
import asyncio
import signal
import sys
from collections.abc import Callable
from pathlib import Path

from pydantic import ValidationError
from structlog.stdlib import BoundLogger

from myao3.application.services.agent_loop import AgentLoop
from myao3.config import (
    ConfigError,
    ConfigFileNotFoundError,
    load_config,
)
from myao3.domain.entities.event import Event
from myao3.infrastructure import EventQueue
from myao3.infrastructure.logging import get_logger, setup_logging
from myao3.infrastructure.tracing import setup_tracing
from myao3.presentation.http.server import HTTPServer

# Shutdown timeout in seconds
SHUTDOWN_TIMEOUT = 30


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        args: Command line arguments. If None, uses sys.argv.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(description="myao3 - Event-driven autonomous bot")
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=Path("config.yaml"),
        help="Path to configuration file (default: config.yaml)",
    )
    return parser.parse_args(args)


async def run_main_loop(
    event_queue: EventQueue,
    agent_loop: AgentLoop,
    shutdown_event: asyncio.Event,
    running_check: Callable[[], bool],
    logger: BoundLogger,
) -> None:
    """Run the main event processing loop.

    Args:
        event_queue: EventQueue instance for retrieving events.
        agent_loop: AgentLoop instance for processing events.
        shutdown_event: Event that signals shutdown.
        running_check: Callable that returns whether the loop should continue.
        logger: Logger instance.
    """
    while running_check():
        # Create tasks for dequeue and shutdown wait
        dequeue_task = asyncio.create_task(event_queue.dequeue())
        shutdown_task = asyncio.create_task(shutdown_event.wait())

        try:
            # Wait for either dequeue to return or shutdown to be signaled
            done, pending = await asyncio.wait(
                [dequeue_task, shutdown_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Cancel pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # Check if shutdown was signaled
            if shutdown_task in done:
                # If dequeue also completed, process that event
                if dequeue_task in done:
                    event = dequeue_task.result()
                    await _process_event(event, agent_loop, event_queue, logger)
                break

            # Process the event
            if dequeue_task in done:
                event = dequeue_task.result()
                await _process_event(event, agent_loop, event_queue, logger)

        except asyncio.CancelledError:
            # Clean up on cancellation
            dequeue_task.cancel()
            shutdown_task.cancel()
            try:
                await dequeue_task
            except asyncio.CancelledError:
                pass
            try:
                await shutdown_task
            except asyncio.CancelledError:
                pass
            raise


async def _process_event(
    event: Event,
    agent_loop: AgentLoop,
    event_queue: EventQueue,
    logger: BoundLogger,
) -> None:
    """Process a single event.

    Args:
        event: Event to process.
        agent_loop: AgentLoop instance.
        event_queue: EventQueue instance for marking done.
        logger: Logger instance.
    """
    try:
        await agent_loop.process(event)
    except Exception as e:
        logger.error("Error processing event", event_id=event.id, error=str(e))
    finally:
        event_queue.mark_done(event)


async def main_async(
    config_path: Path,
    shutdown_timeout: float = SHUTDOWN_TIMEOUT,
) -> int:
    """Async main function.

    Args:
        config_path: Path to configuration file.
        shutdown_timeout: Maximum time in seconds to wait for graceful shutdown.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    # 1. Load configuration
    config = load_config(config_path)

    # 2. Initialize logging
    setup_logging(config.logging)
    logger = get_logger(__name__)
    logger.info("Starting myao3", config_path=str(config_path))

    # 3. Initialize tracing (if OTEL endpoint is configured)
    telemetry = setup_tracing()
    if telemetry:
        logger.info("Tracing enabled")

    # 4. Initialize components
    event_queue = EventQueue()
    agent_loop = AgentLoop(config=config.agent, logger=get_logger("agent"))
    http_server = HTTPServer(
        config=config.server,
        event_queue=event_queue,
        logger=get_logger("http_server"),
    )

    # 5. Setup shutdown handling
    running = True
    shutdown_event = asyncio.Event()

    def is_running() -> bool:
        return running

    def signal_handler(sig: signal.Signals) -> None:
        nonlocal running
        logger.info("Received signal, initiating shutdown", signal=sig.name)
        running = False
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler, sig)

    try:
        # 6. Start HTTP server
        await http_server.start()
        logger.info("myao3 started successfully")

        # 7. Run main loop
        await run_main_loop(
            event_queue=event_queue,
            agent_loop=agent_loop,
            shutdown_event=shutdown_event,
            running_check=is_running,
            logger=logger,
        )

    except asyncio.CancelledError:
        logger.info("Main loop cancelled")

    finally:
        # 8. Shutdown
        logger.info("Shutting down")
        try:
            await asyncio.wait_for(http_server.stop(), timeout=shutdown_timeout)
            logger.info("myao3 stopped")
        except TimeoutError:
            logger.warning(
                "Shutdown timed out, forcing termination",
                timeout_seconds=shutdown_timeout,
            )

    return 0


def main() -> None:
    """Main entry point."""
    args = parse_args()
    config_path = args.config

    try:
        exit_code = asyncio.run(main_async(config_path))
        sys.exit(exit_code)
    except ConfigFileNotFoundError:
        print(f"Error: {config_path} not found", file=sys.stderr)
        sys.exit(1)
    except ConfigError as e:
        print(f"Error: Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValidationError as e:
        print(f"Error: Configuration validation error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
