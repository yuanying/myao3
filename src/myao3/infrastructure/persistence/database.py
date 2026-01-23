"""Database connection management."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlmodel import SQLModel


class Database:
    """Non-blocking database connection manager.

    Manages SQLite database connections using SQLModel and aiosqlite.

    Attributes:
        url: SQLAlchemy connection URL.
        engine: Async database engine (available after initialize()).

    Example:
        >>> database = Database("sqlite+aiosqlite:///./data/myao3.db")
        >>> await database.initialize()
        >>> async with database.get_session() as session:
        ...     result = await session.exec(select(Model))
        >>> await database.close()
    """

    def __init__(self, url: str) -> None:
        """Initialize Database with connection URL.

        Args:
            url: SQLAlchemy-style connection URL.

        Raises:
            ValueError: If URL is empty or invalid format.
        """
        if not url:
            raise ValueError("Database URL cannot be empty")

        self._validate_url(url)
        self._url = url
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    def _validate_url(self, url: str) -> None:
        """Validate URL format.

        Args:
            url: URL to validate.

        Raises:
            ValueError: If URL format is invalid.
        """
        try:
            parsed = urlparse(url)
            if not parsed.scheme or "+" not in parsed.scheme:
                raise ValueError(f"Invalid database URL format: {url}")
        except Exception as e:
            raise ValueError(f"Invalid database URL format: {url}") from e

    @property
    def url(self) -> str:
        """Get the connection URL."""
        return self._url

    @property
    def engine(self) -> AsyncEngine:
        """Get the async engine.

        Returns:
            The async database engine.

        Raises:
            RuntimeError: If database is not initialized.
        """
        if self._engine is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._engine

    async def initialize(self) -> None:
        """Initialize database engine and create tables.

        Creates parent directories for SQLite file if they don't exist,
        then creates the async engine and all registered SQLModel tables.
        """
        self._ensure_parent_directory()

        self._engine = create_async_engine(
            self._url,
            echo=False,
        )

        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        async with self._engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    def _ensure_parent_directory(self) -> None:
        """Create parent directory for SQLite file if it doesn't exist."""
        parsed = urlparse(self._url)
        if parsed.scheme.startswith("sqlite"):
            db_path = parsed.path
            if db_path.startswith("///"):
                db_path = db_path[3:]
            elif db_path.startswith("/"):
                db_path = db_path[1:]

            if db_path:
                parent_dir = Path(db_path).parent
                parent_dir.mkdir(parents=True, exist_ok=True)

    async def close(self) -> None:
        """Close database connection and dispose engine."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

    @asynccontextmanager
    async def get_session(self) -> AsyncIterator[AsyncSession]:
        """Get a database session.

        Yields:
            AsyncSession: Database session with auto-commit on success
                and auto-rollback on exception.

        Raises:
            RuntimeError: If database is not initialized or has been closed.
        """
        if self._session_factory is None:
            raise RuntimeError("Database not initialized or has been closed.")

        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
