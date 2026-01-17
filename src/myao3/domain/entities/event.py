"""Event entity for the event-driven architecture."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

import ulid
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Event type enumeration."""

    PING = "ping"


class Event(BaseModel):
    """Base class for all events."""

    id: str = Field(default_factory=lambda: str(ulid.new()))
    type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str
    payload: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def get_identity_key(self) -> str:
        """Return the identity key for deduplication."""
        return self.id


class PingEvent(Event):
    """Ping event for health check."""

    type: Literal[EventType.PING] = EventType.PING
    source: Literal["api"] = "api"

    def get_identity_key(self) -> str:
        """Return fixed identity key for ping events."""
        return "ping"
