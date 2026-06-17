"""OpenAI chat-completions adapter for LGX handlers."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from openai import OpenAI


class Models:
    """Thin OpenAI adapter used by LangGraph agent nodes."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        self._model = "gpt-4o-mini"
        try:
            openai_key = self.config.get("OPENAI_API_KEY", "")
            self._client = OpenAI(api_key=openai_key) if openai_key else None
        except Exception as exc:
            print(f"Error initializing OpenAI client: {exc}")
            self._client = None

    def complete(self, messages: List[Dict[str, Any]], *, temperature: float = 0.0) -> str:
        if self._client is None:
            return "OpenAI client is not configured (missing OPENAI_API_KEY)."

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
            )
            msg = response.choices[0].message
            return (msg.content or "").strip()
        except Exception as exc:
            print(f"Error running LLM call: {exc}")
            return f"LLM error: {exc}"
