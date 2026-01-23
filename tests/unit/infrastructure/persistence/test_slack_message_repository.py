"""Tests for SlackMessageRepository.

Test cases:
- TC-03-001: メッセージ保存
- TC-03-002: メッセージの upsert（created_at 維持）
- TC-03-003: チャンネルメッセージ取得（新しい順、スレッド返信除外）
- TC-03-004: スレッドメッセージ取得（古い順、親含む）
- TC-03-005: 未読カウント取得
- TC-03-006: 既読マーク
- TC-03-007: 空のチャンネル取得
- TC-03-008: Bot メッセージの保存
- TC-03-009: 複合キーの一意性
- TC-03-010: raw_event の JSON シリアライズ
- TC-03-011: reply_count のインクリメント
- TC-03-012: 存在しないメッセージの reply_count インクリメント
- TC-03-013: get_by_id でメッセージ取得
- TC-03-014: get_by_id で存在しないメッセージ
"""

from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from myao3.domain.entities.slack_message import SlackMessage
from myao3.infrastructure.persistence.database import Database
from myao3.infrastructure.persistence.slack_message_repository import (
    SqliteSlackMessageRepository,
)


@pytest.fixture
async def database(tmp_path: Path) -> AsyncIterator[Database]:
    """Create a test database."""
    db_path = tmp_path / "test.db"
    url = f"sqlite+aiosqlite:///{db_path}"
    db = Database(url)
    await db.initialize()
    yield db
    await db.close()


@pytest.fixture
def repository(database: Database) -> SqliteSlackMessageRepository:
    """Create a repository instance."""
    return SqliteSlackMessageRepository(database)


def create_message(
    channel_id: str = "C123",
    ts: str = "1234567890.123456",
    user_id: str = "U456",
    text: str = "Hello",
    thread_ts: str | None = None,
    is_bot: bool = False,
    is_read: bool = False,
    reply_count: int = 0,
    timestamp: datetime | None = None,
    raw_event: dict | None = None,
    created_at: datetime | None = None,
) -> SlackMessage:
    """Helper to create a SlackMessage."""
    now = datetime.now(timezone.utc)
    return SlackMessage(
        id=f"{channel_id}:{ts}",
        channel_id=channel_id,
        user_id=user_id,
        text=text,
        ts=ts,
        thread_ts=thread_ts,
        is_bot=is_bot,
        is_read=is_read,
        reply_count=reply_count,
        timestamp=timestamp or now,
        raw_event=raw_event or {"type": "message"},
        created_at=created_at or now,
    )


class TestSaveMessage:
    """TC-03-001: メッセージ保存."""

    async def test_save_message(
        self, repository: SqliteSlackMessageRepository, database: Database
    ) -> None:
        """メッセージが正しく保存される."""
        message = create_message()

        await repository.save(message)

        saved = await repository.get_by_id(message.id)
        assert saved is not None
        assert saved.id == message.id
        assert saved.channel_id == message.channel_id
        assert saved.user_id == message.user_id
        assert saved.text == message.text
        assert saved.ts == message.ts
        assert saved.raw_event == message.raw_event


class TestUpsertMessage:
    """TC-03-002: メッセージの upsert（created_at 維持）."""

    async def test_upsert_maintains_created_at(
        self, repository: SqliteSlackMessageRepository
    ) -> None:
        """upsert で created_at が維持される."""
        now = datetime.now(timezone.utc)
        original_created_at = now - timedelta(hours=1)

        message = create_message(
            text="Original",
            created_at=original_created_at,
        )
        await repository.save(message)

        updated_message = create_message(
            text="Updated",
            created_at=now,
        )
        await repository.save(updated_message)

        saved = await repository.get_by_id(message.id)
        assert saved is not None
        assert saved.text == "Updated"
        # created_at は最初の値を維持
        # SQLite から取得した datetime は offset-naive になるため、
        # replace で比較用に変換
        original_naive = original_created_at.replace(tzinfo=None)
        assert abs((saved.created_at - original_naive).total_seconds()) < 1


class TestGetByChannel:
    """TC-03-003: チャンネルメッセージ取得（新しい順、スレッド返信除外）."""

    async def test_get_by_channel_returns_newest_first(
        self, repository: SqliteSlackMessageRepository
    ) -> None:
        """新しい順でソートされて返される."""
        now = datetime.now(timezone.utc)

        messages = [
            create_message(
                ts="1234567890.000001",
                timestamp=now - timedelta(hours=2),
            ),
            create_message(
                ts="1234567890.000003",
                timestamp=now,
            ),
            create_message(
                ts="1234567890.000002",
                timestamp=now - timedelta(hours=1),
            ),
        ]

        for msg in messages:
            await repository.save(msg)

        result = await repository.get_by_channel("C123", limit=10)

        assert len(result) == 3
        # 新しい順でソート
        assert result[0].ts == "1234567890.000003"
        assert result[1].ts == "1234567890.000002"
        assert result[2].ts == "1234567890.000001"

    async def test_get_by_channel_excludes_thread_replies(
        self, repository: SqliteSlackMessageRepository
    ) -> None:
        """スレッド返信は除外される."""
        now = datetime.now(timezone.utc)

        # 親メッセージ
        parent = create_message(
            ts="1234567890.000001",
            timestamp=now,
        )
        # スレッド返信
        reply = create_message(
            ts="1234567890.000002",
            thread_ts="1234567890.000001",
            timestamp=now + timedelta(seconds=1),
        )

        await repository.save(parent)
        await repository.save(reply)

        result = await repository.get_by_channel("C123", limit=10)

        assert len(result) == 1
        assert result[0].ts == "1234567890.000001"

    async def test_get_by_channel_respects_limit(
        self, repository: SqliteSlackMessageRepository
    ) -> None:
        """limit が正しく適用される."""
        now = datetime.now(timezone.utc)

        for i in range(5):
            msg = create_message(
                ts=f"1234567890.00000{i}",
                timestamp=now + timedelta(seconds=i),
            )
            await repository.save(msg)

        result = await repository.get_by_channel("C123", limit=3)

        assert len(result) == 3


class TestGetThread:
    """TC-03-004: スレッドメッセージ取得（古い順、親含む）."""

    async def test_get_thread_includes_parent(
        self, repository: SqliteSlackMessageRepository
    ) -> None:
        """親メッセージが含まれる."""
        now = datetime.now(timezone.utc)
        thread_ts = "1234567890.000001"

        parent = create_message(
            ts=thread_ts,
            timestamp=now,
        )
        reply = create_message(
            ts="1234567890.000002",
            thread_ts=thread_ts,
            timestamp=now + timedelta(seconds=1),
        )

        await repository.save(parent)
        await repository.save(reply)

        result = await repository.get_thread("C123", thread_ts, limit=10)

        assert len(result) == 2
        assert any(msg.ts == thread_ts for msg in result)

    async def test_get_thread_returns_oldest_first(
        self, repository: SqliteSlackMessageRepository
    ) -> None:
        """古い順でソートされて返される."""
        now = datetime.now(timezone.utc)
        thread_ts = "1234567890.000001"

        parent = create_message(
            ts=thread_ts,
            timestamp=now,
        )
        reply1 = create_message(
            ts="1234567890.000002",
            thread_ts=thread_ts,
            timestamp=now + timedelta(seconds=1),
        )
        reply2 = create_message(
            ts="1234567890.000003",
            thread_ts=thread_ts,
            timestamp=now + timedelta(seconds=2),
        )

        await repository.save(parent)
        await repository.save(reply1)
        await repository.save(reply2)

        result = await repository.get_thread("C123", thread_ts, limit=10)

        assert len(result) == 3
        # 古い順でソート
        assert result[0].ts == thread_ts
        assert result[1].ts == "1234567890.000002"
        assert result[2].ts == "1234567890.000003"

    async def test_get_thread_respects_limit(
        self, repository: SqliteSlackMessageRepository
    ) -> None:
        """limit が正しく適用される."""
        now = datetime.now(timezone.utc)
        thread_ts = "1234567890.000001"

        parent = create_message(
            ts=thread_ts,
            timestamp=now,
        )
        await repository.save(parent)

        for i in range(5):
            reply = create_message(
                ts=f"1234567890.00001{i}",
                thread_ts=thread_ts,
                timestamp=now + timedelta(seconds=i + 1),
            )
            await repository.save(reply)

        result = await repository.get_thread("C123", thread_ts, limit=3)

        assert len(result) == 3


class TestGetUnreadCount:
    """TC-03-005: 未読カウント取得."""

    async def test_get_unread_count(
        self, repository: SqliteSlackMessageRepository
    ) -> None:
        """未読メッセージの正確な数が返される."""
        now = datetime.now(timezone.utc)

        # 未読メッセージ
        for i in range(3):
            msg = create_message(
                ts=f"1234567890.00000{i}",
                is_read=False,
                timestamp=now,
            )
            await repository.save(msg)

        # 既読メッセージ
        read_msg = create_message(
            ts="1234567890.000010",
            is_read=True,
            timestamp=now,
        )
        await repository.save(read_msg)

        count = await repository.get_unread_count("C123")

        assert count == 3


class TestMarkAsRead:
    """TC-03-006: 既読マーク."""

    async def test_mark_as_read(self, repository: SqliteSlackMessageRepository) -> None:
        """指定されたメッセージのみ既読になる."""
        now = datetime.now(timezone.utc)

        messages = []
        for i in range(3):
            msg = create_message(
                ts=f"1234567890.00000{i}",
                is_read=False,
                timestamp=now,
            )
            await repository.save(msg)
            messages.append(msg)

        # 最初の2つを既読にマーク
        await repository.mark_as_read([messages[0].id, messages[1].id])

        result1 = await repository.get_by_id(messages[0].id)
        result2 = await repository.get_by_id(messages[1].id)
        result3 = await repository.get_by_id(messages[2].id)

        assert result1 is not None
        assert result2 is not None
        assert result3 is not None
        assert result1.is_read is True
        assert result2.is_read is True
        assert result3.is_read is False


class TestEmptyChannel:
    """TC-03-007: 空のチャンネル取得."""

    async def test_get_by_channel_returns_empty_list(
        self, repository: SqliteSlackMessageRepository
    ) -> None:
        """存在しないチャンネルでは空のリストが返される."""
        result = await repository.get_by_channel("NONEXISTENT", limit=10)

        assert result == []


class TestBotMessage:
    """TC-03-008: Bot メッセージの保存."""

    async def test_save_bot_message(
        self, repository: SqliteSlackMessageRepository
    ) -> None:
        """is_bot が正しく保存される."""
        message = create_message(is_bot=True)

        await repository.save(message)

        saved = await repository.get_by_id(message.id)
        assert saved is not None
        assert saved.is_bot is True


class TestCompositeKeyUniqueness:
    """TC-03-009: 複合キーの一意性."""

    async def test_different_ts_same_channel(
        self, repository: SqliteSlackMessageRepository
    ) -> None:
        """同一チャンネルで異なる ts のメッセージが個別に保存される."""
        now = datetime.now(timezone.utc)

        msg1 = create_message(
            channel_id="C123",
            ts="1234567890.000001",
            timestamp=now,
        )
        msg2 = create_message(
            channel_id="C123",
            ts="1234567890.000002",
            timestamp=now,
        )

        await repository.save(msg1)
        await repository.save(msg2)

        result1 = await repository.get_by_id(msg1.id)
        result2 = await repository.get_by_id(msg2.id)

        assert result1 is not None
        assert result2 is not None
        assert result1.id != result2.id

    async def test_same_ts_different_channel(
        self, repository: SqliteSlackMessageRepository
    ) -> None:
        """同一 ts で異なるチャンネルのメッセージが個別に保存される."""
        now = datetime.now(timezone.utc)

        msg1 = create_message(
            channel_id="C123",
            ts="1234567890.000001",
            timestamp=now,
        )
        msg2 = create_message(
            channel_id="C456",
            ts="1234567890.000001",
            timestamp=now,
        )

        await repository.save(msg1)
        await repository.save(msg2)

        result1 = await repository.get_by_id(msg1.id)
        result2 = await repository.get_by_id(msg2.id)

        assert result1 is not None
        assert result2 is not None
        assert result1.id != result2.id


class TestRawEventSerialization:
    """TC-03-010: raw_event の JSON シリアライズ."""

    async def test_raw_event_serialization(
        self, repository: SqliteSlackMessageRepository
    ) -> None:
        """ネストした dict が正しくシリアライズ・デシリアライズされる."""
        raw_event = {
            "type": "message",
            "subtype": "bot_message",
            "text": "Hello",
            "attachments": [{"title": "Test", "fields": [{"value": "1"}]}],
            "nested": {"level1": {"level2": {"level3": "deep"}}},
        }

        message = create_message(raw_event=raw_event)

        await repository.save(message)

        saved = await repository.get_by_id(message.id)
        assert saved is not None
        assert saved.raw_event == raw_event
        assert saved.raw_event["attachments"][0]["title"] == "Test"
        assert saved.raw_event["nested"]["level1"]["level2"]["level3"] == "deep"


class TestIncrementReplyCount:
    """TC-03-011: reply_count のインクリメント."""

    async def test_increment_reply_count(
        self, repository: SqliteSlackMessageRepository
    ) -> None:
        """reply_count が正しくインクリメントされる."""
        message = create_message(reply_count=0)

        await repository.save(message)

        result = await repository.increment_reply_count(message.id)

        assert result is True

        saved = await repository.get_by_id(message.id)
        assert saved is not None
        assert saved.reply_count == 1

    async def test_increment_reply_count_multiple(
        self, repository: SqliteSlackMessageRepository
    ) -> None:
        """reply_count が複数回インクリメントされる."""
        message = create_message(reply_count=0)

        await repository.save(message)

        await repository.increment_reply_count(message.id)
        await repository.increment_reply_count(message.id)
        await repository.increment_reply_count(message.id)

        saved = await repository.get_by_id(message.id)
        assert saved is not None
        assert saved.reply_count == 3


class TestIncrementReplyCountNonexistent:
    """TC-03-012: 存在しないメッセージの reply_count インクリメント."""

    async def test_increment_reply_count_nonexistent(
        self, repository: SqliteSlackMessageRepository
    ) -> None:
        """存在しないメッセージでは False が返される."""
        result = await repository.increment_reply_count("NONEXISTENT:1234567890.123456")

        assert result is False


class TestGetById:
    """TC-03-013: get_by_id でメッセージ取得."""

    async def test_get_by_id(self, repository: SqliteSlackMessageRepository) -> None:
        """保存したメッセージが正しく取得される."""
        message = create_message()

        await repository.save(message)

        result = await repository.get_by_id(message.id)

        assert result is not None
        assert result.id == message.id
        assert result.text == message.text


class TestGetByIdNonexistent:
    """TC-03-014: get_by_id で存在しないメッセージ."""

    async def test_get_by_id_nonexistent(
        self, repository: SqliteSlackMessageRepository
    ) -> None:
        """存在しないメッセージでは None が返される."""
        result = await repository.get_by_id("NONEXISTENT:1234567890.123456")

        assert result is None
