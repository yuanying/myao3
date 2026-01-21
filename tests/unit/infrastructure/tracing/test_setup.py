"""Tests for tracing setup."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from myao3.infrastructure.tracing.setup import setup_tracing


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """Ensure OTEL_EXPORTER_OTLP_ENDPOINT is not set."""
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    yield


@pytest.fixture
def mock_strands_telemetry() -> Generator[MagicMock]:
    """Mock StrandsTelemetry class."""
    with patch("myao3.infrastructure.tracing.setup.StrandsTelemetry") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        yield mock_cls


class TestSetupTracing:
    """Tests for setup_tracing function."""

    def test_returns_none_when_endpoint_not_set(
        self,
        clean_env: None,
        mock_strands_telemetry: MagicMock,
    ) -> None:
        """When OTEL_EXPORTER_OTLP_ENDPOINT is not set, returns None."""
        result = setup_tracing()

        assert result is None
        mock_strands_telemetry.assert_not_called()

    def test_initializes_telemetry_when_endpoint_set(
        self,
        monkeypatch: pytest.MonkeyPatch,
        mock_strands_telemetry: MagicMock,
    ) -> None:
        """When OTEL_EXPORTER_OTLP_ENDPOINT is set, initializes StrandsTelemetry."""
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
        monkeypatch.delenv("OTEL_SERVICE_NAME", raising=False)

        result = setup_tracing()

        mock_strands_telemetry.assert_called_once_with()
        mock_strands_telemetry.return_value.setup_otlp_exporter.assert_called_once()
        assert result == mock_strands_telemetry.return_value
        # Verify default service name is set
        import os

        assert os.environ.get("OTEL_SERVICE_NAME") == "myao3"

    def test_handles_empty_endpoint_as_not_set(
        self,
        monkeypatch: pytest.MonkeyPatch,
        mock_strands_telemetry: MagicMock,
    ) -> None:
        """When OTEL_EXPORTER_OTLP_ENDPOINT is empty string, returns None."""
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")

        result = setup_tracing()

        assert result is None
        mock_strands_telemetry.assert_not_called()

    def test_preserves_existing_service_name(
        self,
        monkeypatch: pytest.MonkeyPatch,
        mock_strands_telemetry: MagicMock,
    ) -> None:
        """When OTEL_SERVICE_NAME is already set, does not override it."""
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
        monkeypatch.setenv("OTEL_SERVICE_NAME", "custom-service")

        setup_tracing()

        import os

        assert os.environ.get("OTEL_SERVICE_NAME") == "custom-service"
