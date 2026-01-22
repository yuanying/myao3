"""Pydantic models for application configuration."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class SlackConfig(BaseModel):
    """Slack integration configuration."""

    bot_token: str = Field(
        ...,
        description=(
            "Slack bot token used for Web API calls (typically starts with 'xoxb-')."
        ),
    )
    app_token: str = Field(
        ...,
        description=(
            "Slack app-level token used for Socket Mode connections "
            "(typically starts with 'xapp-')."
        ),
    )
    response_delay: float = Field(
        default=480.0,
        description="Base delay in seconds before the bot responds to a message.",
    )
    response_delay_jitter: float = Field(
        default=240.0,
        description=(
            "Maximum additional random jitter in seconds added to the base "
            "response_delay."
        ),
    )
    context_messages: int = Field(
        default=30,
        description=(
            "Maximum number of recent messages from the Slack channel or "
            "conversation to include as context when generating a response."
        ),
    )
    thread_messages: int = Field(
        default=10,
        description=(
            "Maximum number of recent messages from the current Slack thread "
            "to include when constructing a threaded reply."
        ),
    )


class DatabaseConfig(BaseModel):
    """Database connection configuration."""

    url: str = Field(
        ...,
        description=(
            "SQLAlchemy-style database connection URL "
            "(e.g., 'sqlite+aiosqlite:///path/to/db')."
        ),
    )


class LLMConfig(BaseModel):
    """LLM configuration for LiteLLM."""

    model_id: str
    params: dict[str, Any] = Field(default_factory=dict)
    client_args: dict[str, Any] = Field(default_factory=dict)


class AgentConfig(BaseModel):
    """Agent configuration."""

    system_prompt: str
    llm: LLMConfig


class ServerConfig(BaseModel):
    """HTTP server configuration."""

    host: str = "0.0.0.0"
    port: int = 8080


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    format: Literal["json", "text"] = "json"


class AppConfig(BaseModel):
    """Application configuration."""

    agent: AgentConfig
    server: ServerConfig = Field(default_factory=ServerConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    slack: SlackConfig | None = None
    database: DatabaseConfig | None = None
