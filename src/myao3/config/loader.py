"""Configuration loader with environment variable expansion."""

import os
import re
from pathlib import Path
from typing import Any

import yaml

from myao3.config.models import AppConfig

# Regex pattern for environment variable: matches ${VAR_NAME} exactly
ENV_VAR_PATTERN = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")


class ConfigError(Exception):
    """Base exception for configuration errors."""


class ConfigFileNotFoundError(ConfigError):
    """Raised when the configuration file is not found."""


class ConfigParseError(ConfigError):
    """Raised when the YAML file cannot be parsed."""


class EnvVarNotFoundError(ConfigError):
    """Raised when an environment variable is not found."""


def expand_env_vars(data: Any) -> Any:
    """Expand environment variables in the configuration data.

    Only expands complete string values matching ${VAR_NAME} pattern.
    Does not expand partial matches like "prefix${VAR}suffix".

    Args:
        data: Configuration data (dict, list, or scalar value).

    Returns:
        Data with environment variables expanded.

    Raises:
        EnvVarNotFoundError: If an environment variable is not defined.
    """
    if isinstance(data, dict):
        return {key: expand_env_vars(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [expand_env_vars(item) for item in data]
    elif isinstance(data, str):
        match = ENV_VAR_PATTERN.match(data)
        if match:
            var_name = match.group(1)
            value = os.environ.get(var_name)
            if value is None:
                raise EnvVarNotFoundError(
                    f"Environment variable '{var_name}' not found"
                )
            return value
        return data
    else:
        return data


def load_config(path: Path) -> AppConfig:
    """Load and validate configuration from a YAML file.

    Args:
        path: Path to the YAML configuration file.

    Returns:
        Validated AppConfig instance.

    Raises:
        ConfigFileNotFoundError: If the file does not exist.
        ConfigParseError: If the YAML cannot be parsed.
        EnvVarNotFoundError: If an environment variable is not defined.
        ValidationError: If the configuration fails Pydantic validation.
    """
    if not path.exists():
        raise ConfigFileNotFoundError(f"Configuration file not found: {path}")

    try:
        with open(path) as f:
            raw_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigParseError(f"Failed to parse YAML: {e}") from e

    if raw_data is None:
        raw_data = {}

    expanded_data = expand_env_vars(raw_data)
    return AppConfig(**expanded_data)
