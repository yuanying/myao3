"""Tests for Database class.

Test cases:
- TC-02-001: Database 初期化
- TC-02-002: テーブル自動作成
- TC-02-003: セッション取得
- TC-02-004: 自動コミット
- TC-02-005: 自動ロールバック
- TC-02-006: ディレクトリ自動作成
- TC-02-007: Database クローズ
- TC-02-008: 並行セッション処理
"""

import asyncio
from pathlib import Path
from typing import Optional

import pytest
from sqlalchemy import text
from sqlmodel import Field, SQLModel

from myao3.infrastructure.persistence.database import Database


class SampleModel(SQLModel, table=True):
    """Test model for database tests."""

    __tablename__ = "test_model"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


class TestDatabaseInitialization:
    """TC-02-001: Database 初期化."""

    async def test_database_initialize_creates_file(self, tmp_path: Path) -> None:
        """Database.initialize() で SQLite ファイルが作成される."""
        db_path = tmp_path / "test.db"
        url = f"sqlite+aiosqlite:///{db_path}"

        database = Database(url)
        await database.initialize()

        assert db_path.exists()

        await database.close()

    async def test_database_url_property(self, tmp_path: Path) -> None:
        """URL プロパティが正しく返される."""
        db_path = tmp_path / "test.db"
        url = f"sqlite+aiosqlite:///{db_path}"

        database = Database(url)

        assert database.url == url

    async def test_database_engine_property_after_initialize(
        self, tmp_path: Path
    ) -> None:
        """初期化後に engine プロパティが利用可能."""
        db_path = tmp_path / "test.db"
        url = f"sqlite+aiosqlite:///{db_path}"

        database = Database(url)
        await database.initialize()

        assert database.engine is not None

        await database.close()

    async def test_database_invalid_url_raises_error(self) -> None:
        """不正な URL で ValueError が発生."""
        with pytest.raises(ValueError):
            Database("")

    async def test_database_invalid_url_format_raises_error(self) -> None:
        """不正な URL 形式で ValueError が発生."""
        with pytest.raises(ValueError):
            Database("invalid-url")


class TestTableCreation:
    """TC-02-002: テーブル自動作成."""

    async def test_tables_created_on_initialize(self, tmp_path: Path) -> None:
        """initialize() でテーブルが自動作成される."""
        db_path = tmp_path / "test.db"
        url = f"sqlite+aiosqlite:///{db_path}"

        database = Database(url)
        await database.initialize()

        async with database.get_session() as session:
            result = await session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            tables = [row[0] for row in result.fetchall()]

        assert "test_model" in tables

        await database.close()


class TestSessionManagement:
    """TC-02-003: セッション取得."""

    async def test_get_session_returns_async_session(self, tmp_path: Path) -> None:
        """get_session() で AsyncSession が返される."""
        db_path = tmp_path / "test.db"
        url = f"sqlite+aiosqlite:///{db_path}"

        database = Database(url)
        await database.initialize()

        async with database.get_session() as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1

        await database.close()


class TestAutoCommit:
    """TC-02-004: 自動コミット."""

    async def test_session_auto_commits_on_exit(self, tmp_path: Path) -> None:
        """コンテキストマネージャを抜けると自動コミットされる."""
        db_path = tmp_path / "test.db"
        url = f"sqlite+aiosqlite:///{db_path}"

        database = Database(url)
        await database.initialize()

        async with database.get_session() as session:
            test_record = SampleModel(name="test_name")
            session.add(test_record)

        async with database.get_session() as session:
            result = await session.execute(text("SELECT name FROM test_model"))
            names = [row[0] for row in result.fetchall()]

        assert "test_name" in names

        await database.close()


class TestAutoRollback:
    """TC-02-005: 自動ロールバック."""

    async def test_session_auto_rollbacks_on_exception(self, tmp_path: Path) -> None:
        """例外発生時に自動ロールバックされる."""
        db_path = tmp_path / "test.db"
        url = f"sqlite+aiosqlite:///{db_path}"

        database = Database(url)
        await database.initialize()

        with pytest.raises(ValueError):
            async with database.get_session() as session:
                test_record = SampleModel(name="rollback_test")
                session.add(test_record)
                raise ValueError("Test exception")

        async with database.get_session() as session:
            result = await session.execute(text("SELECT name FROM test_model"))
            names = [row[0] for row in result.fetchall()]

        assert "rollback_test" not in names

        await database.close()


class TestDirectoryCreation:
    """TC-02-006: ディレクトリ自動作成."""

    async def test_parent_directory_auto_created(self, tmp_path: Path) -> None:
        """存在しない親ディレクトリが自動作成される."""
        nested_path = tmp_path / "nested" / "dir" / "test.db"
        url = f"sqlite+aiosqlite:///{nested_path}"

        database = Database(url)
        await database.initialize()

        assert nested_path.parent.exists()
        assert nested_path.exists()

        await database.close()


class TestDatabaseClose:
    """TC-02-007: Database クローズ."""

    async def test_close_disposes_engine(self, tmp_path: Path) -> None:
        """close() でエンジンが破棄される."""
        db_path = tmp_path / "test.db"
        url = f"sqlite+aiosqlite:///{db_path}"

        database = Database(url)
        await database.initialize()
        await database.close()

        with pytest.raises(RuntimeError):
            async with database.get_session() as session:
                await session.execute(text("SELECT 1"))


class TestConcurrentSessions:
    """TC-02-008: 並行セッション処理."""

    async def test_concurrent_sessions_work(self, tmp_path: Path) -> None:
        """複数セッションが並行して動作する."""
        db_path = tmp_path / "test.db"
        url = f"sqlite+aiosqlite:///{db_path}"

        database = Database(url)
        await database.initialize()

        async def insert_record(name: str) -> None:
            async with database.get_session() as session:
                test_record = SampleModel(name=name)
                session.add(test_record)

        await asyncio.gather(
            insert_record("concurrent_1"),
            insert_record("concurrent_2"),
            insert_record("concurrent_3"),
        )

        async with database.get_session() as session:
            result = await session.execute(text("SELECT name FROM test_model"))
            names = [row[0] for row in result.fetchall()]

        assert "concurrent_1" in names
        assert "concurrent_2" in names
        assert "concurrent_3" in names

        await database.close()
