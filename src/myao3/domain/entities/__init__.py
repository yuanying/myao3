"""Domain entities."""

from myao3.domain.entities.event import Event, EventType, PingEvent
from myao3.domain.entities.slack_message import SlackMessage

__all__ = ["Event", "EventType", "PingEvent", "SlackMessage"]
