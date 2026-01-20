"""Tests for HTTPServer."""

import asyncio

import aiohttp
import pytest
import structlog
from aiohttp.test_utils import TestClient

from myao3.config.models import ServerConfig
from myao3.domain.entities.event import PingEvent
from myao3.infrastructure.event_queue import EventQueue
from myao3.presentation.http.server import HTTPServer


@pytest.fixture
def event_queue() -> EventQueue:
    return EventQueue()


@pytest.fixture
def logger() -> structlog.BoundLogger:
    return structlog.get_logger()


@pytest.fixture
def http_server(event_queue: EventQueue, logger: structlog.BoundLogger) -> HTTPServer:
    config = ServerConfig(host="127.0.0.1", port=8080)
    return HTTPServer(config=config, event_queue=event_queue, logger=logger)


@pytest.fixture
async def client(http_server: HTTPServer, aiohttp_client) -> TestClient:
    return await aiohttp_client(http_server.create_app())


class TestHTTPServer:
    """Tests for HTTPServer class."""

    async def test_health_check(self, client: TestClient) -> None:
        """TC-08-007: Health check endpoint returns ok status."""
        response = await client.get("/healthz")

        assert response.status == 200
        data = await response.json()
        assert data == {"status": "ok"}

    async def test_content_type_is_json(self, client: TestClient) -> None:
        """TC-08-010: Response Content-Type is application/json."""
        response = await client.get("/healthz")

        assert response.status == 200
        assert response.content_type == "application/json"

    async def test_ping_event_received(
        self, client: TestClient, event_queue: EventQueue
    ) -> None:
        """TC-08-001: Ping event is received and enqueued."""
        response = await client.post(
            "/api/v1/events",
            json={"type": "ping"},
        )

        assert response.status == 200
        data = await response.json()
        assert "event_id" in data

        # Verify the event is enqueued
        event = await asyncio.wait_for(event_queue.dequeue(), timeout=1.0)
        assert isinstance(event, PingEvent)
        assert event.id == data["event_id"]

    async def test_missing_type_field(self, client: TestClient) -> None:
        """TC-08-005: Request without type field returns 400."""
        response = await client.post(
            "/api/v1/events",
            json={"payload": {}},
        )

        assert response.status == 400
        data = await response.json()
        assert data == {"error": "Missing required field: type"}

    async def test_invalid_json(self, client: TestClient) -> None:
        """TC-08-004: Invalid JSON returns 400."""
        response = await client.post(
            "/api/v1/events",
            data="not json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status == 400
        data = await response.json()
        assert data == {"error": "Invalid JSON"}

    async def test_invalid_event_type(self, client: TestClient) -> None:
        """TC-08-006: Unknown event type returns 400."""
        response = await client.post(
            "/api/v1/events",
            json={"type": "unknown"},
        )

        assert response.status == 400
        data = await response.json()
        assert data == {"error": "Invalid event type: unknown"}

    async def test_event_with_payload(
        self, client: TestClient, event_queue: EventQueue
    ) -> None:
        """TC-08-003: Event with payload is correctly enqueued."""
        payload = {"key": "value", "nested": {"data": 123}}
        response = await client.post(
            "/api/v1/events",
            json={"type": "ping", "payload": payload},
        )

        assert response.status == 200

        event = await asyncio.wait_for(event_queue.dequeue(), timeout=1.0)
        assert event.payload == payload

    async def test_event_with_delay(
        self, client: TestClient, event_queue: EventQueue
    ) -> None:
        """TC-08-002: Event with delay is enqueued after delay."""
        response = await client.post(
            "/api/v1/events",
            json={"type": "ping", "delay": 0.1},
        )

        assert response.status == 200

        # Event should not be immediately available
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(event_queue.dequeue(), timeout=0.05)

        # Event should be available after delay
        event = await asyncio.wait_for(event_queue.dequeue(), timeout=0.2)
        assert isinstance(event, PingEvent)

    async def test_server_config_host_port(
        self, event_queue: EventQueue, logger: structlog.BoundLogger
    ) -> None:
        """TC-08-009: Server uses host and port from config."""
        config = ServerConfig(host="127.0.0.1", port=9000)
        server = HTTPServer(config=config, event_queue=event_queue, logger=logger)

        assert server.config.host == "127.0.0.1"
        assert server.config.port == 9000

    async def test_server_start_stop(
        self, event_queue: EventQueue, logger: structlog.BoundLogger
    ) -> None:
        """TC-08-008: Server can be started and stopped."""
        config = ServerConfig(host="127.0.0.1", port=0)
        server = HTTPServer(config=config, event_queue=event_queue, logger=logger)

        await server.start()
        try:
            assert server.is_running

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://127.0.0.1:{server.actual_port}/healthz"
                ) as response:
                    assert response.status == 200
        finally:
            await server.stop()

        assert not server.is_running
