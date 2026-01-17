"""Mock LLM model for testing."""

from typing import Any, AsyncGenerator, AsyncIterable, TypeVar

from strands.models import Model
from strands.types.content import Messages
from strands.types.streaming import StreamEvent

T = TypeVar("T")


class MockModel(Model):
    """Mock model for testing without actual LLM API calls."""

    def __init__(self, raise_error: bool = False) -> None:
        """Initialize the mock model.

        Args:
            raise_error: If True, raise an error on stream.
        """
        self._raise_error = raise_error
        self._config: dict[str, Any] = {}

    async def stream(
        self,
        messages: Messages,
        tool_specs: list[Any] | None = None,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterable[StreamEvent]:
        """Stream mock response.

        Args:
            messages: The messages to process.
            tool_specs: Tool specifications (unused in mock).
            system_prompt: System prompt (unused in mock).
            **kwargs: Additional keyword arguments.

        Yields:
            Mock stream events.

        Raises:
            RuntimeError: If raise_error is True.
        """
        if self._raise_error:
            raise RuntimeError("Mock LLM error for testing")

        yield {
            "contentBlockStart": {
                "contentBlockIndex": 0,
                "start": {"text": ""},
            }
        }
        yield {
            "contentBlockDelta": {
                "delta": {"text": "Mock LLM response"},
                "contentBlockIndex": 0,
            }
        }
        yield {
            "contentBlockStop": {
                "contentBlockIndex": 0,
            }
        }
        yield {"messageStop": {"stopReason": "end_turn"}}

    async def structured_output(
        self,
        output_model: type[T],
        prompt: Messages,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, T | Any], None]:
        """Return structured output (not implemented for mock).

        Args:
            output_model: The output model type.
            prompt: The prompt messages.
            **kwargs: Additional keyword arguments.

        Yields:
            Empty dict (not implemented).
        """
        yield {}
        return

    def update_config(self, **model_config: Any) -> None:
        """Update model configuration.

        Args:
            **model_config: Configuration to update.
        """
        self._config.update(model_config)

    def get_config(self) -> dict[str, Any]:
        """Get model configuration.

        Returns:
            The current configuration.
        """
        return self._config
