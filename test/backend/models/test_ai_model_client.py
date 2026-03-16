"""Tests for AIModelClient environment variable handling and interface."""

from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from backend.models.ai_model_client import AIModelClient


def test_client_is_disabled_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AI_MODEL_API_KEY", raising=False)
    client = AIModelClient()
    assert client.enabled is False


def test_client_is_enabled_with_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_MODEL_API_KEY", "test-key-123")
    monkeypatch.setenv("AI_MODEL_URL", "https://api.example.com/v1/chat/completions")
    client = AIModelClient()
    assert client.enabled is True


def test_client_reads_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_MODEL_API_KEY", "my-secret-key")
    client = AIModelClient()
    assert client.api_key == "my-secret-key"


def test_client_reads_url_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_MODEL_URL", "https://custom.api.example.com/v1/chat/completions")
    client = AIModelClient()
    assert client.endpoint == "https://custom.api.example.com/v1/chat/completions"


def test_constructor_kwargs_override_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_MODEL_API_KEY", "env-key")
    monkeypatch.setenv("AI_MODEL_URL", "https://env.example.com")
    client = AIModelClient(api_key="override-key", endpoint="https://override.example.com")
    assert client.api_key == "override-key"
    assert client.endpoint == "https://override.example.com"


def test_chat_json_raises_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AI_MODEL_API_KEY", raising=False)
    client = AIModelClient()
    with pytest.raises(RuntimeError, match="AI_MODEL_API_KEY"):
        client.chat_json(model="test-model", system_prompt="sys", user_prompt="user")


def test_chat_json_sends_correct_request(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_MODEL_API_KEY", "test-key")
    monkeypatch.setenv("AI_MODEL_URL", "https://api.example.com/v1/chat/completions")
    client = AIModelClient()

    mock_response_body = json.dumps({
        "choices": [{"message": {"content": '{"result": "ok"}'}}]
    }).encode("utf-8")

    mock_response = MagicMock()
    mock_response.read.return_value = mock_response_body
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("backend.models.ai_model_client.urlopen", return_value=mock_response) as mock_urlopen:
        result = client.chat_json(model="claude-sonnet-4-6", system_prompt="sys", user_prompt="user")

    assert result == {"result": "ok"}
    called_request = mock_urlopen.call_args[0][0]
    assert called_request.get_header("Authorization") == "Bearer test-key"
    assert called_request.full_url == "https://api.example.com/v1/chat/completions"

    sent_payload = json.loads(called_request.data.decode("utf-8"))
    assert sent_payload["model"] == "claude-sonnet-4-6"
    assert sent_payload["messages"][0]["role"] == "system"
    assert sent_payload["messages"][1]["role"] == "user"
