"""Tests for SlackMessage entity.

Test cases:
- SlackMessage インスタンス作成
- SQLModel テーブルとして定義されていることの確認
- thread_ts がオプショナルであることの確認
"""

from datetime import datetime, timezone

from sqlmodel import SQLModel

from myao3.domain.entities.slack_message import SlackMessage


class TestSlackMessageEntity:
    """SlackMessage エンティティのテスト."""

    def test_create_slack_message(self) -> None:
        """SlackMessage インスタンスが正しく作成される."""
        now = datetime.now(timezone.utc)
        raw_event = {"type": "message", "text": "Hello"}

        message = SlackMessage(
            id="C123:1234567890.123456",
            channel_id="C123",
            user_id="U456",
            text="Hello",
            ts="1234567890.123456",
            timestamp=now,
            raw_event=raw_event,
            created_at=now,
        )

        assert message.id == "C123:1234567890.123456"
        assert message.channel_id == "C123"
        assert message.user_id == "U456"
        assert message.text == "Hello"
        assert message.ts == "1234567890.123456"
        assert message.thread_ts is None
        assert message.is_bot is False
        assert message.is_read is False
        assert message.reply_count == 0
        assert message.timestamp == now
        assert message.raw_event == raw_event
        assert message.created_at == now

    def test_slack_message_is_table(self) -> None:
        """SlackMessage が SQLModel テーブルとして定義されている."""
        assert issubclass(SlackMessage, SQLModel)
        assert hasattr(SlackMessage, "__tablename__")
        assert SlackMessage.__tablename__ == "slack_messages"

    def test_thread_ts_is_optional(self) -> None:
        """thread_ts がオプショナルであることを確認."""
        now = datetime.now(timezone.utc)

        # thread_ts なしで作成可能
        message = SlackMessage(
            id="C123:1234567890.123456",
            channel_id="C123",
            user_id="U456",
            text="Hello",
            ts="1234567890.123456",
            timestamp=now,
            raw_event={},
            created_at=now,
        )
        assert message.thread_ts is None

        # thread_ts ありで作成可能
        message_with_thread = SlackMessage(
            id="C123:1234567890.234567",
            channel_id="C123",
            user_id="U456",
            text="Reply",
            ts="1234567890.234567",
            thread_ts="1234567890.123456",
            timestamp=now,
            raw_event={},
            created_at=now,
        )
        assert message_with_thread.thread_ts == "1234567890.123456"

    def test_is_bot_default(self) -> None:
        """is_bot のデフォルト値が False であることを確認."""
        now = datetime.now(timezone.utc)
        message = SlackMessage(
            id="C123:1234567890.123456",
            channel_id="C123",
            user_id="U456",
            text="Hello",
            ts="1234567890.123456",
            timestamp=now,
            raw_event={},
            created_at=now,
        )
        assert message.is_bot is False

    def test_is_read_default(self) -> None:
        """is_read のデフォルト値が False であることを確認."""
        now = datetime.now(timezone.utc)
        message = SlackMessage(
            id="C123:1234567890.123456",
            channel_id="C123",
            user_id="U456",
            text="Hello",
            ts="1234567890.123456",
            timestamp=now,
            raw_event={},
            created_at=now,
        )
        assert message.is_read is False

    def test_reply_count_default(self) -> None:
        """reply_count のデフォルト値が 0 であることを確認."""
        now = datetime.now(timezone.utc)
        message = SlackMessage(
            id="C123:1234567890.123456",
            channel_id="C123",
            user_id="U456",
            text="Hello",
            ts="1234567890.123456",
            timestamp=now,
            raw_event={},
            created_at=now,
        )
        assert message.reply_count == 0
