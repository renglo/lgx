"""Renglo platform adapter used by LGX agent nodes."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from renglo.agent.websocket_client import WebSocketClient

from .class_prototypes import SessionEvent
from .models import Models
from .sessions import Sessions

_logger = logging.getLogger(__name__)


class RengloAdapter:
    """
    Bridges LangGraph nodes to Renglo sessions, LLM, WebSocket delivery, and audit events.
    """

    def __init__(
        self,
        *,
        sessions: Sessions,
        models: Models,
        ws_client: WebSocketClient,
        connection_id: str = "",
        portfolio: str = "",
        org: str = "",
        on_stream: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        self._sessions = sessions
        self._models = models
        self._ws = ws_client
        self._connection_id = connection_id
        self._portfolio = portfolio
        self._org = org
        self._on_stream = on_stream

    def load_session_state(self, session_id: str) -> Dict[str, Any]:
        """Rebuild LangGraph message history from session turn events."""
        messages: List[Dict[str, Any]] = []
        for event in self._sessions.get_events(session_id):
            if event.event_type == "user_message":
                messages.append(
                    {
                        "role": "user",
                        "content": event.payload.get("text") or event.payload.get("message") or "",
                        "timestamp": event.timestamp.isoformat(),
                    }
                )
            elif event.event_type == "assistant_message":
                messages.append(
                    {
                        "role": "assistant",
                        "content": event.payload.get("text") or event.payload.get("message") or "",
                        "timestamp": event.timestamp.isoformat(),
                    }
                )
        return {"messages": messages}

    def save_session_state(self, session_id: str, state: Dict[str, Any]) -> None:
        """No-op: graph nodes persist transcript rows via ``log_event`` on the active turn."""
        del session_id, state

    def _send_roll_ws(self, event_type: str, text: str) -> None:
        role = "user" if event_type == "user_message" else "assistant"
        doc = {
            "_type": event_type,
            "_out": {"role": role, "content": text},
        }
        if self._connection_id and self._ws.is_configured():
            self._ws.send_message(self._connection_id, doc)

    def call_llm(
        self,
        *,
        org_id: str,
        messages: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        del org_id, metadata
        llm_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
            if m.get("role") in {"system", "user", "assistant"} and m.get("content")
        ]
        return self._models.complete(llm_messages)

    def send_message(
        self,
        *,
        channel: str,
        session_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        del channel, session_id
        doc = {
            "_type": "assistant_message",
            "_out": {"role": "assistant", "content": text},
        }
        if self._connection_id and self._ws.is_configured():
            self._ws.send_message(self._connection_id, doc)

    def log_event(
        self,
        *,
        session_id: str,
        event_type: str,
        payload: Dict[str, Any],
    ) -> None:
        if session_id != self._sessions.session_id:
            return
        try:
            if event_type == "inbound_message":
                ev = SessionEvent(
                    event_id=str(uuid.uuid4()),
                    session_id=session_id,
                    event_type="user_message",
                    timestamp=datetime.utcnow(),
                    payload={"text": payload.get("message", "")},
                )
            elif event_type == "llm_response":
                ev = SessionEvent(
                    event_id=str(uuid.uuid4()),
                    session_id=session_id,
                    event_type="assistant_message",
                    timestamp=datetime.utcnow(),
                    payload={"text": payload.get("response_text", "")},
                )
            elif event_type == "outbound_message":
                ev = SessionEvent(
                    event_id=str(uuid.uuid4()),
                    session_id=session_id,
                    event_type="lgx_event",
                    timestamp=datetime.utcnow(),
                    payload={"event_type": event_type, **payload},
                )
            else:
                ev = SessionEvent(
                    event_id=str(uuid.uuid4()),
                    session_id=session_id,
                    event_type="lgx_event",
                    timestamp=datetime.utcnow(),
                    payload={"event_type": event_type, **payload},
                )
            self._sessions.append_event(ev)
        except Exception as exc:
            _logger.warning("Failed to persist event %s: %s", event_type, exc)
            return

        if event_type == "inbound_message":
            text = str(payload.get("message") or payload.get("text") or "")
            if text:
                self._send_roll_ws("user_message", text)
        elif self._on_stream and event_type not in {"llm_response", "outbound_message"}:
            self._on_stream(
                {
                    "channel": "lgx_event",
                    "event_type": event_type,
                    "payload": payload,
                }
            )
