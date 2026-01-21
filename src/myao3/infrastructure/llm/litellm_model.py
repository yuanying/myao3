"""LLM model factory."""

import os

from strands.models.litellm import LiteLLMModel
from strands.models.ollama import OllamaModel

from myao3.config.models import LLMConfig
from myao3.infrastructure.llm.mock_model import MockModel

# Union type for all supported models
Model = LiteLLMModel | OllamaModel | MockModel


def create_model(config: LLMConfig) -> Model:
    """Create a model based on configuration and environment.

    Args:
        config: LLM configuration.

    Returns:
        MockModel if MOCK_LLM=true, OllamaModel if model_id starts with "ollama/",
        otherwise LiteLLMModel.
    """
    mock_llm = os.getenv("MOCK_LLM", "").lower()

    if mock_llm == "true":
        return MockModel()

    if mock_llm == "error":
        return MockModel(raise_error=True)

    # Use OllamaModel for ollama models
    if config.model_id.startswith("ollama/"):
        return _create_ollama_model(config)

    return LiteLLMModel(
        model_id=config.model_id,
        params=config.params,
        client_args=config.client_args,
    )


def _create_ollama_model(config: LLMConfig) -> OllamaModel:
    """Create an OllamaModel from LLMConfig.

    Args:
        config: LLM configuration with model_id starting with "ollama/".

    Returns:
        Configured OllamaModel instance.
    """
    # Extract model name (remove "ollama/" prefix)
    model_id = config.model_id.removeprefix("ollama/")

    # Extract host from client_args
    host = config.client_args.get("api_base")

    # Pass through params directly to OllamaModel
    return OllamaModel(host=host, model_id=model_id, **config.params)
