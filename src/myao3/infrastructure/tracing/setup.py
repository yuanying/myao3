"""Tracing setup for OpenTelemetry integration."""

import os

from strands.telemetry import StrandsTelemetry

DEFAULT_SERVICE_NAME = "myao3"


def setup_tracing() -> StrandsTelemetry | None:
    """Initialize tracing if OTEL endpoint is configured.

    Sets OTEL_SERVICE_NAME to "myao3" if not already configured.

    Returns:
        StrandsTelemetry instance if OTEL_EXPORTER_OTLP_ENDPOINT is set,
        None otherwise.
    """
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return None

    # Set default service name if not already configured
    if not os.environ.get("OTEL_SERVICE_NAME"):
        os.environ["OTEL_SERVICE_NAME"] = DEFAULT_SERVICE_NAME

    telemetry = StrandsTelemetry()
    telemetry.setup_otlp_exporter()
    return telemetry
