"""SQLite implementation of SlackMessageRepository."""

from typing import Any

from sqlalchemy import text
from sqlmodel import select

from myao3.domain.entities.slack_message import SlackMessage
from myao3.infrastructure.persistence.database import Database


class SqliteSlackMessageRepository:
    """SQLite implementation of SlackMessageRepository.

    Uses SQLModel with async SQLite for message persistence.
    """

    def __init__(self, database: Database) -> None:
        """Initialize the repository.

        Args:
            database: Database instance for session management.
        """
        self._database = database

    async def save(self, message: SlackMessage) -> None:
        """Save a message (upsert).

        If a message with the same ID exists, it will be updated
        while preserving the original created_at value.

        Args:
            message: The message to save.
        """
        async with self._database.get_session() as session:
            existing = await session.get(SlackMessage, message.id)

            if existing:
                # Update existing record, preserve created_at
                existing.channel_id = message.channel_id
                existing.user_id = message.user_id
                existing.text = message.text
                existing.thread_ts = message.thread_ts
                existing.ts = message.ts
                existing.is_bot = message.is_bot
                existing.is_read = message.is_read
                existing.reply_count = message.reply_count
                existing.timestamp = message.timestamp
                existing.raw_event = message.raw_event
                # created_at is preserved
                session.add(existing)
            else:
                session.add(message)

    async def get_by_id(self, message_id: str) -> SlackMessage | None:
        """Get a message by ID.

        Args:
            message_id: The message ID in format `{channel_id}:{ts}`.

        Returns:
            The message if found, None otherwise.
        """
        async with self._database.get_session() as session:
            return await session.get(SlackMessage, message_id)

    async def get_by_channel(self, channel_id: str, limit: int) -> list[SlackMessage]:
        """Get messages from a channel.

        Returns messages sorted by timestamp descending (newest first).
        Thread replies (messages with thread_ts) are excluded.

        Args:
            channel_id: The channel ID.
            limit: Maximum number of messages to return.

        Returns:
            List of messages.
        """
        async with self._database.get_session() as session:
            statement = (
                select(SlackMessage)
                .where(SlackMessage.channel_id == channel_id)
                .where(SlackMessage.thread_ts.is_(None))  # type: ignore[union-attr]
                .order_by(SlackMessage.timestamp.desc())  # type: ignore[union-attr]
                .limit(limit)
            )
            result = await session.execute(statement)
            return list(result.scalars().all())

    async def get_thread(
        self, channel_id: str, thread_ts: str, limit: int
    ) -> list[SlackMessage]:
        """Get messages from a thread.

        Returns messages sorted by timestamp ascending (oldest first).
        Includes the parent message (where ts == thread_ts).

        Args:
            channel_id: The channel ID.
            thread_ts: The thread's parent message ts.
            limit: Maximum number of messages to return.

        Returns:
            List of messages.
        """
        async with self._database.get_session() as session:
            # Get parent message (ts == thread_ts) and replies (thread_ts == thread_ts)
            statement = (
                select(SlackMessage)
                .where(SlackMessage.channel_id == channel_id)
                .where(
                    (SlackMessage.ts == thread_ts)
                    | (SlackMessage.thread_ts == thread_ts)
                )
                .order_by(SlackMessage.timestamp.asc())  # type: ignore[union-attr]
                .limit(limit)
            )
            result = await session.execute(statement)
            return list(result.scalars().all())

    async def get_unread_count(self, channel_id: str) -> int:
        """Get the count of unread messages in a channel.

        Args:
            channel_id: The channel ID.

        Returns:
            Number of unread messages.
        """
        async with self._database.get_session() as session:
            result = await session.execute(
                text(
                    "SELECT COUNT(*) FROM slack_messages "
                    "WHERE channel_id = :channel_id AND is_read = 0"
                ),
                {"channel_id": channel_id},
            )
            count = result.scalar()
            return count if count else 0

    async def mark_as_read(self, message_ids: list[str]) -> None:
        """Mark messages as read.

        Args:
            message_ids: List of message IDs to mark as read.
        """
        if not message_ids:
            return

        async with self._database.get_session() as session:
            # Use SQLAlchemy's update with in_() for safe bulk update
            from sqlalchemy import update

            stmt = (
                update(SlackMessage)
                .where(SlackMessage.id.in_(message_ids))  # type: ignore[union-attr]
                .values(is_read=True)
            )
            await session.execute(stmt)

    async def increment_reply_count(self, message_id: str) -> bool:
        """Increment the reply count of a message.

        Args:
            message_id: The message ID.

        Returns:
            True if the message was found and updated, False otherwise.
        """
        async with self._database.get_session() as session:
            result: Any = await session.execute(
                text(
                    "UPDATE slack_messages SET reply_count = reply_count + 1 "
                    "WHERE id = :message_id"
                ),
                {"message_id": message_id},
            )
            return result.rowcount > 0
