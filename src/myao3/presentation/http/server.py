"""HTTP server for receiving events."""

import json

import structlog
from aiohttp import web

from myao3.config.models import ServerConfig
from myao3.domain.entities.event import EventType, PingEvent
from myao3.infrastructure.event_queue import EventQueue


class HTTPServer:
    """HTTP server for receiving events and health checks.

    This server provides endpoints for:
    - POST /api/v1/events: Receive and enqueue events
    - GET /healthz: Kubernetes liveness probe

    Args:
        config: Server configuration containing host and port.
        event_queue: EventQueue instance for enqueuing received events.
        logger: Structured logger for logging.
    """

    # Mapping from event type string to event class
    EVENT_TYPE_MAP: dict[str, type] = {
        EventType.PING.value: PingEvent,
    }

    def __init__(
        self,
        config: ServerConfig,
        event_queue: EventQueue,
        logger: structlog.BoundLogger,
    ) -> None:
        self.config = config
        self._event_queue = event_queue
        self._logger = logger
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None

    @property
    def is_running(self) -> bool:
        """Return True if the server is running."""
        return self._site is not None

    @property
    def actual_port(self) -> int:
        """Return the actual port the server is listening on.

        This is useful when port 0 is configured to get a random port.

        Raises:
            RuntimeError: If the server is not running.
        """
        if self._site is None:
            raise RuntimeError("Server is not running")
        # Access internal server via getattr to avoid type checker issues
        # with aiohttp's internal implementation
        server = getattr(self._site, "_server", None)
        if server is None:
            raise RuntimeError("Server is not running")
        sockets = getattr(server, "sockets", None)
        if sockets:
            return sockets[0].getsockname()[1]
        raise RuntimeError("No sockets available")

    def create_app(self) -> web.Application:
        """Create and return the aiohttp Application.

        This method is exposed for testing purposes.

        Returns:
            Configured aiohttp Application.
        """
        app = web.Application()
        app.router.add_get("/healthz", self._handle_health_check)
        app.router.add_post("/api/v1/events", self._handle_event)
        return app

    async def start(self) -> None:
        """Start the HTTP server."""
        self._app = self.create_app()
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self.config.host, self.config.port)
        await self._site.start()
        self._logger.info(
            "HTTP server started",
            host=self.config.host,
            port=self.actual_port,
        )

    async def stop(self) -> None:
        """Stop the HTTP server."""
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None
            self._site = None
            self._app = None
            self._logger.info("HTTP server stopped")

    async def _handle_health_check(self, request: web.Request) -> web.Response:
        """Handle GET /healthz requests.

        Args:
            request: The incoming request.

        Returns:
            JSON response with status "ok".
        """
        return web.json_response({"status": "ok"})

    async def _handle_event(self, request: web.Request) -> web.Response:
        """Handle POST /api/v1/events requests.

        Args:
            request: The incoming request.

        Returns:
            JSON response with event_id on success, or error message on failure.
        """
        # Parse JSON body
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON"}, status=400)

        # Validate required fields
        if "type" not in body:
            return web.json_response(
                {"error": "Missing required field: type"}, status=400
            )

        event_type = body["type"]

        # Validate event type
        if event_type not in self.EVENT_TYPE_MAP:
            return web.json_response(
                {"error": f"Invalid event type: {event_type}"}, status=400
            )

        # Create and enqueue event
        event_class = self.EVENT_TYPE_MAP[event_type]
        payload = body.get("payload", {})
        delay = body.get("delay", 0)

        try:
            event = event_class(payload=payload)
        except Exception as e:
            self._logger.error("Failed to create event", error=str(e))
            return web.json_response({"error": "Failed to create event"}, status=500)

        try:
            await self._event_queue.enqueue(event, delay=delay)
        except Exception as e:
            self._logger.error("Failed to enqueue event", error=str(e))
            return web.json_response({"error": "Failed to enqueue event"}, status=500)

        self._logger.info(
            "Event received",
            event_id=event.id,
            event_type=event_type,
            delay=delay,
        )

        return web.json_response({"event_id": event.id})
