"""SlackMessageRepository protocol."""

from typing import Protocol

from myao3.domain.entities.slack_message import SlackMessage


class SlackMessageRepository(Protocol):
    """Repository protocol for Slack messages.

    Defines the interface for persisting and retrieving Slack messages.
    """

    async def save(self, message: SlackMessage) -> None:
        """Save a message (upsert).

        If a message with the same ID exists, it will be updated.
        The created_at field is preserved on update.

        Args:
            message: The message to save.
        """
        ...

    async def get_by_id(self, message_id: str) -> SlackMessage | None:
        """Get a message by ID.

        Args:
            message_id: The message ID in format `{channel_id}:{ts}`.

        Returns:
            The message if found, None otherwise.
        """
        ...

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
        ...

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
        ...

    async def get_unread_count(self, channel_id: str) -> int:
        """Get the count of unread messages in a channel.

        Args:
            channel_id: The channel ID.

        Returns:
            Number of unread messages.
        """
        ...

    async def mark_as_read(self, message_ids: list[str]) -> None:
        """Mark messages as read.

        Args:
            message_ids: List of message IDs to mark as read.
        """
        ...

    async def increment_reply_count(self, message_id: str) -> bool:
        """Increment the reply count of a message.

        Args:
            message_id: The message ID.

        Returns:
            True if the message was found and updated, False otherwise.
        """
        ...
