"""SlackMessage entity for Slack message persistence."""

from datetime import datetime
from typing import Any

from sqlalchemy import Column, Index
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel


class SlackMessage(SQLModel, table=True):
    """Slack message entity.

    Represents a Slack message stored in the database.

    Attributes:
        id: Composite key in format `{channel_id}:{ts}`.
        channel_id: Slack channel ID.
        user_id: Sender's user ID.
        text: Message content.
        thread_ts: Parent message's ts for thread replies.
        ts: Slack timestamp.
        is_bot: Whether message is from a bot.
        is_read: Whether message has been read by LLM.
        reply_count: Number of thread replies (for parent messages).
        timestamp: Message sent time.
        raw_event: Original Slack event data.
        created_at: Record creation time.
    """

    __tablename__ = "slack_messages"
    __table_args__ = (
        Index("idx_channel_timestamp", "channel_id", "timestamp"),
        Index("idx_thread", "channel_id", "thread_ts", "timestamp"),
        Index("idx_unread", "channel_id", "is_read"),
    )

    id: str = Field(primary_key=True)
    channel_id: str = Field(index=True)
    user_id: str = Field(index=True)
    text: str
    thread_ts: str | None = Field(default=None, index=True)
    ts: str
    is_bot: bool = Field(default=False)
    is_read: bool = Field(default=False, index=True)
    reply_count: int = Field(default=0)
    timestamp: datetime
    raw_event: dict[str, Any] = Field(sa_column=Column(JSON))
    created_at: datetime
