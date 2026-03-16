"""Generic AI model HTTP client with OpenAI-compatible chat completions API."""

from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen


class AIModelClient:
    """HTTP client for OpenAI-compatible chat completion endpoints."""

    def __init__(self, api_key: str | None = None, endpoint: str | None = None):
        self.api_key = api_key or os.getenv("AI_MODEL_API_KEY", "")
        self.endpoint = endpoint or os.getenv("AI_MODEL_URL", "")

    @property
    def enabled_api_key(self) -> bool:
        return bool(self.api_key)

    @property
    def enabled_endpoint(self) -> bool:
        return bool(self.endpoint)

    @property
    def enabled(self) -> bool:
        return self.enabled_api_key and self.enabled_endpoint

    def chat_json(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
    ) -> dict:
        """Send chat completion request and parse JSON output.

        Returns:
            Parsed JSON dict from assistant content.
        """

        if not self.enabled_api_key:
            raise RuntimeError("AI_MODEL_API_KEY is not set")

        if not self.enabled_endpoint:
            raise RuntimeError("AI_MODEL_URL is not set")

        payload = {
            "model": model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        request = Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))

        content = body["choices"][0]["message"]["content"]
        return _extract_json(content)


def _extract_json(content: str) -> dict:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    return json.loads(text)
