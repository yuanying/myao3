"""Pydantic models for application configuration."""

from typing import Any, Literal

from pydantic import BaseModel, Field


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
