"""Tests for EventHandler implementations."""

from myao3.application.handlers import EventHandler
from myao3.application.handlers.event_handlers import (
    EventHandlerRegistry,
    PingEventHandler,
)
from myao3.domain.entities.event import EventType, PingEvent


class TestPingEventHandler:
    """Tests for PingEventHandler class."""

    def test_build_query_returns_expected_string(self) -> None:
        """TC-06-003: PingEventHandler.build_query() returns expected string."""
        handler = PingEventHandler()
        event = PingEvent()

        result = handler.build_query(event)

        assert "System ping received" in result
        assert "Check your status" in result

    def test_implements_event_handler_protocol(self) -> None:
        """PingEventHandler implements EventHandler protocol."""
        handler = PingEventHandler()

        assert isinstance(handler, EventHandler)


class TestEventHandlerRegistry:
    """Tests for EventHandlerRegistry class."""

    def test_register_and_get_handler(self) -> None:
        """TC-06-008: EventHandlerRegistry returns registered handler."""
        registry = EventHandlerRegistry()
        handler = PingEventHandler()

        registry.register(EventType.PING, handler)
        result = registry.get_handler(EventType.PING)

        assert result is handler

    def test_get_handler_returns_none_for_unregistered(self) -> None:
        """EventHandlerRegistry returns None for unregistered event type."""
        registry = EventHandlerRegistry()

        result = registry.get_handler(EventType.PING)

        assert result is None

    def test_register_overwrites_existing_handler(self) -> None:
        """Registering handler for same event type overwrites existing."""
        registry = EventHandlerRegistry()
        handler1 = PingEventHandler()
        handler2 = PingEventHandler()

        registry.register(EventType.PING, handler1)
        registry.register(EventType.PING, handler2)
        result = registry.get_handler(EventType.PING)

        assert result is handler2
