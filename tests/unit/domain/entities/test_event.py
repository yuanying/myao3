"""Tests for Event entity."""

from datetime import datetime, timedelta, timezone

from myao3.domain.entities.event import Event, EventType, PingEvent

TIMESTAMP_TOLERANCE_SECONDS = 5


class TestPingEvent:
    """Tests for PingEvent class."""

    def test_event_id_is_ulid_format(self) -> None:
        """TC-04-001: Event ID is auto-generated in ULID format (26 chars)."""
        event = PingEvent()

        assert len(event.id) == 26
        assert event.id.isalnum()

    def test_event_ids_are_unique(self) -> None:
        """TC-04-001: Multiple events have unique IDs."""
        event1 = PingEvent()
        event2 = PingEvent()

        assert event1.id != event2.id

    def test_created_at_is_auto_set(self) -> None:
        """TC-04-002: created_at is automatically set to current time."""
        before = datetime.now(timezone.utc)
        event = PingEvent()
        after = datetime.now(timezone.utc)

        assert isinstance(event.created_at, datetime)
        assert event.created_at.tzinfo is not None
        assert (
            before - timedelta(seconds=TIMESTAMP_TOLERANCE_SECONDS)
            <= event.created_at
            <= after + timedelta(seconds=TIMESTAMP_TOLERANCE_SECONDS)
        )

    def test_identity_key_returns_ping(self) -> None:
        """TC-04-003: PingEvent.get_identity_key() returns 'ping'."""
        event1 = PingEvent()
        event2 = PingEvent()

        assert event1.get_identity_key() == "ping"
        assert event2.get_identity_key() == "ping"

    def test_payload_defaults_to_empty_dict(self) -> None:
        """TC-04-007: payload defaults to empty dict."""
        event = PingEvent()

        assert event.payload == {}

    def test_type_is_ping(self) -> None:
        """PingEvent has type set to PING."""
        event = PingEvent()

        assert event.type == EventType.PING

    def test_source_is_api(self) -> None:
        """PingEvent has source set to 'api'."""
        event = PingEvent()

        assert event.source == "api"


class TestEvent:
    """Tests for Event base class."""

    def test_identity_key_returns_id(self) -> None:
        """TC-04-006: Event.get_identity_key() returns the event id."""
        event = Event(type=EventType.PING, source="test")

        assert event.get_identity_key() == event.id

    def test_event_id_is_ulid_format(self) -> None:
        """Event ID is auto-generated in ULID format (26 chars)."""
        event = Event(type=EventType.PING, source="test")

        assert len(event.id) == 26
        assert event.id.isalnum()

    def test_timestamp_defaults_to_current_time(self) -> None:
        """Event timestamp defaults to current time."""
        before = datetime.now(timezone.utc)
        event = Event(type=EventType.PING, source="test")
        after = datetime.now(timezone.utc)

        assert isinstance(event.timestamp, datetime)
        assert event.timestamp.tzinfo is not None
        assert (
            before - timedelta(seconds=TIMESTAMP_TOLERANCE_SECONDS)
            <= event.timestamp
            <= after + timedelta(seconds=TIMESTAMP_TOLERANCE_SECONDS)
        )

    def test_context_defaults_to_none(self) -> None:
        """Event context defaults to None."""
        event = Event(type=EventType.PING, source="test")

        assert event.context is None
