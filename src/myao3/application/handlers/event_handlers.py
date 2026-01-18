"""Event handler implementations."""

from jinja2 import Template

from myao3.application.handlers import EventHandler
from myao3.domain.entities.event import Event, EventType

PING_QUERY_TEMPLATE = Template(
    "System ping received. Check your status and decide if any action is needed."
)


class PingEventHandler:
    """Handler for ping events."""

    def build_query(self, event: Event) -> str:
        """Build query prompt for ping event.

        Args:
            event: The ping event.

        Returns:
            The query prompt string.
        """
        return PING_QUERY_TEMPLATE.render(event=event)


class EventHandlerRegistry:
    """Registry for event handlers."""

    def __init__(self) -> None:
        """Initialize the registry."""
        self._handlers: dict[EventType, EventHandler] = {}

    def register(self, event_type: EventType, handler: EventHandler) -> None:
        """Register a handler for an event type.

        Args:
            event_type: The event type to handle.
            handler: The handler to register.
        """
        self._handlers[event_type] = handler

    def get_handler(self, event_type: EventType) -> EventHandler | None:
        """Get handler for an event type.

        Args:
            event_type: The event type.

        Returns:
            The handler if registered, None otherwise.
        """
        return self._handlers.get(event_type)
