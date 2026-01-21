"""Tests for LLM model factory."""

import pytest
from strands.models.litellm import LiteLLMModel
from strands.models.ollama import OllamaModel

from myao3.config.models import LLMConfig
from myao3.infrastructure.llm.litellm_model import create_model
from myao3.infrastructure.llm.mock_model import MockModel


class TestCreateModel:
    """Tests for create_model factory function."""

    def test_returns_mock_model_when_mock_llm_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """create_model returns MockModel when MOCK_LLM=true."""
        monkeypatch.setenv("MOCK_LLM", "true")
        config = LLMConfig(model_id="anthropic/claude-sonnet-4-20250514")

        model = create_model(config)

        assert isinstance(model, MockModel)

    def test_returns_mock_model_when_mock_llm_true_uppercase(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """create_model returns MockModel when MOCK_LLM=TRUE (case insensitive)."""
        monkeypatch.setenv("MOCK_LLM", "TRUE")
        config = LLMConfig(model_id="anthropic/claude-sonnet-4-20250514")

        model = create_model(config)

        assert isinstance(model, MockModel)

    def test_returns_litellm_model_when_mock_llm_not_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """create_model returns LiteLLMModel when MOCK_LLM is not set."""
        monkeypatch.delenv("MOCK_LLM", raising=False)
        config = LLMConfig(model_id="anthropic/claude-sonnet-4-20250514")

        model = create_model(config)

        assert isinstance(model, LiteLLMModel)

    def test_returns_litellm_model_when_mock_llm_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """create_model returns LiteLLMModel when MOCK_LLM=false."""
        monkeypatch.setenv("MOCK_LLM", "false")
        config = LLMConfig(model_id="anthropic/claude-sonnet-4-20250514")

        model = create_model(config)

        assert isinstance(model, LiteLLMModel)


class TestCreateOllamaModel:
    """Tests for create_model with ollama models."""

    def test_returns_ollama_model_for_ollama_prefix(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """create_model returns OllamaModel when model_id starts with 'ollama/'."""
        monkeypatch.delenv("MOCK_LLM", raising=False)
        config = LLMConfig(
            model_id="ollama/llama3:8b",
            client_args={"api_base": "http://localhost:11434"},
        )

        model = create_model(config)

        assert isinstance(model, OllamaModel)

    def test_ollama_model_strips_prefix(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OllamaModel receives model_id without 'ollama/' prefix."""
        monkeypatch.delenv("MOCK_LLM", raising=False)
        config = LLMConfig(
            model_id="ollama/llama3:8b",
            client_args={"api_base": "http://localhost:11434"},
        )

        model = create_model(config)

        assert isinstance(model, OllamaModel)
        assert model.config["model_id"] == "llama3:8b"

    def test_ollama_model_accepts_api_base(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """OllamaModel is created with client_args.api_base as host."""
        monkeypatch.delenv("MOCK_LLM", raising=False)
        config = LLMConfig(
            model_id="ollama/llama3:8b",
            client_args={"api_base": "http://example.com:11434"},
        )

        # Should not raise an exception
        model = create_model(config)

        assert isinstance(model, OllamaModel)

    def test_ollama_model_passes_temperature(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """OllamaModel receives temperature from params."""
        monkeypatch.delenv("MOCK_LLM", raising=False)
        config = LLMConfig(
            model_id="ollama/llama3:8b",
            params={"temperature": 0.7},
        )

        model = create_model(config)

        assert isinstance(model, OllamaModel)
        assert model.config["temperature"] == 0.7

    def test_ollama_model_passes_max_tokens(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """OllamaModel receives max_tokens from params."""
        monkeypatch.delenv("MOCK_LLM", raising=False)
        config = LLMConfig(
            model_id="ollama/llama3:8b",
            params={"max_tokens": 1000},
        )

        model = create_model(config)

        assert isinstance(model, OllamaModel)
        assert model.config["max_tokens"] == 1000


class TestMockModel:
    """Tests for MockModel class."""

    @pytest.mark.asyncio
    async def test_stream_returns_mock_response(self) -> None:
        """MockModel.stream() returns mock response."""
        model = MockModel()

        events = []
        async for event in model.stream(messages=[], system_prompt="test"):
            events.append(event)

        assert len(events) >= 2
        has_content = any("contentBlockDelta" in e for e in events)
        has_stop = any("messageStop" in e for e in events)
        assert has_content
        assert has_stop

    @pytest.mark.asyncio
    async def test_stream_response_contains_mock_text(self) -> None:
        """MockModel.stream() response contains 'Mock LLM response'."""
        model = MockModel()

        events = []
        async for event in model.stream(messages=[], system_prompt="test"):
            events.append(event)

        text_events = [e for e in events if "contentBlockDelta" in e]
        text_content = "".join(
            e["contentBlockDelta"]["delta"].get("text", "") for e in text_events
        )
        assert "Mock LLM response" in text_content
