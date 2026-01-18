"""Event handler module."""

from typing import Protocol, runtime_checkable

from myao3.domain.entities.event import Event


@runtime_checkable
class EventHandler(Protocol):
    """Protocol for event handlers that build query prompts."""

    def build_query(self, event: Event) -> str:
        """Build query prompt from event.

        Args:
            event: The event to build query from.

        Returns:
            The query prompt string.
        """
        ...
