"""Tests for logging setup module."""

import json
import logging
import re
from datetime import datetime, timezone

import pytest

from myao3.config.models import LoggingConfig
from myao3.infrastructure.logging import get_logger, setup_logging


class TestSetupLogging:
    """Tests for setup_logging function."""

    def setup_method(self) -> None:
        """Reset logging configuration before each test."""
        # Clear all handlers from root logger
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        root_logger.setLevel(logging.WARNING)

    def test_json_format_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        """TC-03-001: JSON形式でログ出力される。"""
        config = LoggingConfig(level="INFO", format="json")
        setup_logging(config)

        logger = get_logger("test")
        logger.info("Event processed")

        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip())

        assert "timestamp" in log_entry
        assert log_entry["level"] == "info"
        assert log_entry["event"] == "Event processed"

    def test_json_format_includes_required_fields(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """TC-03-001: 必須フィールド（timestamp, level, event）が含まれる。"""
        config = LoggingConfig(level="INFO", format="json")
        setup_logging(config)

        logger = get_logger("test")
        logger.info("Test message")

        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip())

        assert "timestamp" in log_entry
        assert "level" in log_entry
        assert "event" in log_entry

    def test_log_level_filtering_debug_not_shown(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """TC-03-002: INFOレベル設定時、DEBUGログは出力されない。"""
        config = LoggingConfig(level="INFO", format="json")
        setup_logging(config)

        logger = get_logger("test")
        logger.debug("Debug message")

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_log_level_filtering_info_shown(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """TC-03-002: INFOレベル設定時、INFOログは出力される。"""
        config = LoggingConfig(level="INFO", format="json")
        setup_logging(config)

        logger = get_logger("test")
        logger.info("Info message")

        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip())
        assert log_entry["event"] == "Info message"

    def test_log_level_filtering_debug_level(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """TC-03-002: DEBUGレベル設定時、DEBUGログも出力される。"""
        config = LoggingConfig(level="DEBUG", format="json")
        setup_logging(config)

        logger = get_logger("test")
        logger.debug("Debug message")

        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip())
        assert log_entry["event"] == "Debug message"

    def test_context_binding(self, capsys: pytest.CaptureFixture[str]) -> None:
        """TC-03-003: bindしたコンテキストがログに含まれる。"""
        config = LoggingConfig(level="INFO", format="json")
        setup_logging(config)

        logger = get_logger("test")
        bound_logger = logger.bind(event_id="01HXYZ", event_type="ping")
        bound_logger.info("Processing event")

        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip())

        assert log_entry["event_id"] == "01HXYZ"
        assert log_entry["event_type"] == "ping"
        assert log_entry["event"] == "Processing event"

    def test_exception_logging(self, capsys: pytest.CaptureFixture[str]) -> None:
        """TC-03-004: 例外情報がログに含まれる。"""
        config = LoggingConfig(level="INFO", format="json")
        setup_logging(config)

        logger = get_logger("test")

        try:
            raise ValueError("Test error")
        except ValueError:
            logger.exception("An error occurred")

        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip())

        assert log_entry["event"] == "An error occurred"
        assert "exception" in log_entry
        assert "ValueError" in log_entry["exception"]
        assert "Test error" in log_entry["exception"]

    def test_timestamp_iso8601_format(self, capsys: pytest.CaptureFixture[str]) -> None:
        """TC-03-005: タイムスタンプがISO 8601形式である。"""
        config = LoggingConfig(level="INFO", format="json")
        setup_logging(config)

        logger = get_logger("test")
        logger.info("Test message")

        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip())

        timestamp = log_entry["timestamp"]
        # ISO 8601 format: YYYY-MM-DDTHH:MM:SS.ffffffZ
        iso8601_pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z"
        assert re.match(iso8601_pattern, timestamp) is not None

    def test_timestamp_is_utc(self, capsys: pytest.CaptureFixture[str]) -> None:
        """TC-03-005: タイムスタンプがUTC時刻である。"""
        config = LoggingConfig(level="INFO", format="json")
        setup_logging(config)

        before = datetime.now(timezone.utc)
        logger = get_logger("test")
        logger.info("Test message")
        after = datetime.now(timezone.utc)

        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip())

        timestamp_str = log_entry["timestamp"]
        # Parse the timestamp (remove trailing Z and parse)
        log_time = datetime.fromisoformat(timestamp_str.rstrip("Z")).replace(
            tzinfo=timezone.utc
        )

        assert before <= log_time <= after

    def test_text_format_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        """textフォーマット設定時、テキスト形式で出力される。"""
        config = LoggingConfig(level="INFO", format="text")
        setup_logging(config)

        logger = get_logger("test")
        logger.info("Text message")

        captured = capsys.readouterr()
        # Text format should not be valid JSON
        with pytest.raises(json.JSONDecodeError):
            json.loads(captured.out.strip())

        # But should contain the message
        assert "Text message" in captured.out


class TestGetLogger:
    """Tests for get_logger function."""

    def setup_method(self) -> None:
        """Reset logging configuration before each test."""
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        root_logger.setLevel(logging.WARNING)

    def test_get_logger_with_name(self, capsys: pytest.CaptureFixture[str]) -> None:
        """名前付きロガーを取得できる。"""
        config = LoggingConfig(level="INFO", format="json")
        setup_logging(config)

        logger = get_logger("mymodule")
        logger.info("Test message")

        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip())

        assert log_entry["event"] == "Test message"
        assert log_entry["logger"] == "mymodule"

    def test_get_logger_without_name(self, capsys: pytest.CaptureFixture[str]) -> None:
        """名前なしでロガーを取得できる。"""
        config = LoggingConfig(level="INFO", format="json")
        setup_logging(config)

        logger = get_logger()
        logger.info("Test message")

        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip())

        assert log_entry["event"] == "Test message"

    def test_get_logger_returns_bound_logger(self) -> None:
        """get_loggerがBoundLoggerを返す。"""
        config = LoggingConfig(level="INFO", format="json")
        setup_logging(config)

        logger = get_logger("test")

        # Should have bind method
        assert hasattr(logger, "bind")
        assert callable(logger.bind)

        # Should have standard logging methods
        assert hasattr(logger, "info")
        assert hasattr(logger, "debug")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")
        assert hasattr(logger, "exception")
