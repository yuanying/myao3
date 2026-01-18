"""LiteLLM model factory."""

import os

from strands.models.litellm import LiteLLMModel

from myao3.config.models import LLMConfig
from myao3.infrastructure.llm.mock_model import MockModel


def create_model(config: LLMConfig) -> LiteLLMModel | MockModel:
    """Create a model based on configuration and environment.

    Args:
        config: LLM configuration.

    Returns:
        MockModel if MOCK_LLM=true, otherwise LiteLLMModel.
    """
    mock_llm = os.getenv("MOCK_LLM", "").lower()

    if mock_llm == "true":
        return MockModel()

    if mock_llm == "error":
        return MockModel(raise_error=True)

    return LiteLLMModel(
        model_id=config.model_id,
        params=config.params,
        client_args=config.client_args,
    )
