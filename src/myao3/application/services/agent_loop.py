"""Agent loop implementation."""

from typing import Any

from strands import Agent
from structlog.stdlib import BoundLogger

from myao3.application.handlers.event_handlers import (
    EventHandlerRegistry,
    PingEventHandler,
)
from myao3.config.models import AgentConfig
from myao3.domain.entities.event import Event, EventType
from myao3.infrastructure.llm.litellm_model import create_model


class AgentLoop:
    """Agent loop for processing events using LLM.

    Each event is processed as a one-shot invocation with a fresh Agent instance.
    """

    def __init__(self, config: AgentConfig, logger: BoundLogger) -> None:
        """Initialize the agent loop.

        Args:
            config: Agent configuration.
            logger: Logger instance.
        """
        self._logger = logger
        self._config = config
        self._system_prompt = config.system_prompt
        self._handler_registry = self._create_handler_registry()

    def _create_handler_registry(self) -> EventHandlerRegistry:
        """Create and configure the event handler registry.

        Returns:
            Configured EventHandlerRegistry.
        """
        registry = EventHandlerRegistry()
        registry.register(EventType.PING, PingEventHandler())
        return registry

    async def process(self, event: Event) -> str | None:
        """Process an event using the agent.

        Args:
            event: The event to process.

        Returns:
            The LLM response text, or None if no handler found.
            Note: Per FR-AGENT-001 in requirements.md, this method's return type
            is defined as None. The response is returned for debugging/testing
            purposes only and is not used by callers.

        Raises:
            Exception: If LLM invocation fails.
        """
        self._logger.info(
            "Processing event",
            event_id=event.id,
            event_type=event.type.value,
        )

        try:
            handler = self._handler_registry.get_handler(event.type)
            if handler is None:
                self._logger.warning(
                    "No handler found for event type",
                    event_type=event.type.value,
                )
                return None

            query = handler.build_query(event)
            self._logger.debug("Built query", query=query)

            # Create fresh Agent for each event processing.
            # Each event is independent and does not share conversation history,
            # so we use a new Agent instance per invocation (one-shot).
            model = create_model(self._config.llm)
            agent = Agent(
                model=model,
                system_prompt=self._system_prompt,
                tools=[],
            )
            result = await agent.invoke_async(query)

            response_text = self._extract_response_text(result)

            self._logger.info(
                "Event processing completed",
                event_id=event.id,
                response_length=len(response_text) if response_text else 0,
            )

            return response_text

        except Exception as e:
            self._logger.error(
                "Error processing event",
                event_id=event.id,
                error=str(e),
                exc_info=True,
            )
            raise

    def _extract_response_text(self, result: Any) -> str | None:
        """Extract text from agent result.

        Args:
            result: The agent result object.

        Returns:
            The extracted text or None.
        """
        if result is None:
            return None

        if hasattr(result, "message"):
            message: dict[str, Any] = result.message
            if isinstance(message, dict) and "content" in message:
                content: list[dict[str, Any]] = message["content"]
                if isinstance(content, list) and len(content) > 0:
                    first_block = content[0]
                    if isinstance(first_block, dict) and "text" in first_block:
                        text: str = first_block["text"]
                        return text

        return str(result)
