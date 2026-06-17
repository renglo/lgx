"""
LGX conversational agent for Renglo.

Uses the LangGraph library for turn flow (load context → LLM → respond → persist)
and Renglo for sessions, LLM calls, outbound messaging, and audit logging.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from renglo.agent.websocket_client import WebSocketClient
from renglo.common import load_config
from renglo.session.session_controller import SessionController

from .models import Models
from .renglo_adapter import RengloAdapter
from .sessions import Sessions

class AgentState(TypedDict, total=False):
    session_id: str
    user_id: str
    org_id: str
    channel: str
    inbound_message: str
    messages: List[Dict[str, Any]]
    response_text: str
    should_send: bool
    metadata: Dict[str, Any]


@dataclass
class RequestContext:
    connection_id: str = ""
    portfolio: str = ""
    org: str = ""
    public_user: str = ""
    entity_type: str = ""
    entity_id: str = ""
    thread: str = ""
    message: str = ""


request_context: ContextVar[RequestContext] = ContextVar(
    "lgx_request_context",
    default=RequestContext(),
)


class DemoLgxAgent:
    """Simple conversational LangGraph agent using Renglo as the platform layer."""

    def __init__(self) -> None:
        self.config = load_config()
        self.SSC = SessionController(config=self.config)
        ws_url = str(self.config.get("WEBSOCKET_CONNECTIONS", "") or "")
        self._ws = WebSocketClient(ws_url)
        self._sessions: Optional[Sessions] = None
        self._renglo: Optional[RengloAdapter] = None
        self.graph = self._build_graph()

    def _get_context(self) -> RequestContext:
        return request_context.get()

    def _set_context(self, context: RequestContext) -> None:
        request_context.set(context)

    def _send_ws(self, doc: Dict[str, Any], connection_id: Optional[str] = None) -> bool:
        cid = connection_id or self._get_context().connection_id
        if not cid or not self._ws.is_configured():
            return False
        return self._ws.send_message(cid, doc)

    def on_stream(self, message: Dict[str, Any]) -> None:
        body = {"channel": "lgx_stream", **message}
        doc = {
            "_type": "lgx_stream",
            "_out": {"role": "assistant", "content": json.dumps(body, default=str)},
        }
        self._send_ws(doc)

    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        action = "run > demo_lgx_agent"
        context = RequestContext()

        if isinstance(payload, str):
            try:
                payload = json.loads(payload) if payload.strip() else {}
            except json.JSONDecodeError:
                payload = {}
        payload = payload if isinstance(payload, dict) else {}

        if "connectionId" in payload:
            context.connection_id = payload["connectionId"]
        if "portfolio" in payload:
            context.portfolio = payload["portfolio"]
        else:
            return {"success": False, "action": action, "input": payload, "output": "No portfolio provided"}
        if "org" in payload:
            context.org = payload["org"]
        else:
            context.org = "_all"
        if "public_user" in payload:
            context.public_user = payload["public_user"]
        if "entity_type" in payload:
            context.entity_type = payload["entity_type"]
        else:
            context.entity_type = "ag1"
        if "entity_id" in payload:
            context.entity_id = payload["entity_id"]
        else:
            context.entity_id = "5678a"
        if "thread" in payload:
            context.thread = payload["thread"]
        else:
            context.thread = "1234c"
        if "data" in payload:
            context.message = payload["data"]

        self._set_context(context)

        ss = Sessions(
            session_controller=self.SSC,
            portfolio=context.portfolio,
            org=context.org,
            entity_type=context.entity_type,
            entity_id=context.entity_id,
            thread_id=context.thread,
        )
        self._sessions = ss

        ll = Models(config=self.config)
        renglo = RengloAdapter(
            sessions=ss,
            models=ll,
            ws_client=self._ws,
            connection_id=context.connection_id,
            portfolio=context.portfolio,
            org=context.org,
            on_stream=self.on_stream,
        )
        self._renglo = renglo

        try:
            ss.create_turn(
                {
                    "portfolio": context.portfolio,
                    "org": context.org,
                    "public_user": context.public_user or False,
                    "entity_type": context.entity_type,
                    "entity_id": context.entity_id,
                    "thread": context.thread,
                }
            )

            session_id = ss.session_id
            existing_state = renglo.load_session_state(session_id)
            inbound_message = context.message or payload.get("message") or ""

            initial_state: AgentState = {
                **existing_state,
                "session_id": session_id,
                "user_id": payload.get("public_user") or payload.get("user_id"),
                "org_id": context.org,
                "channel": payload.get("channel", "whatsapp"),
                "inbound_message": inbound_message,
                "metadata": payload.get("metadata", {}),
            }

            final_state = self.graph.invoke(initial_state)
            renglo.save_session_state(session_id, dict(final_state))

            summary = {
                "session_id": session_id,
                "response_text": final_state.get("response_text"),
                "sent": final_state.get("should_send", False),
            }
            return {
                "success": True,
                "action": action,
                "input": payload,
                "output": summary,
            }
        finally:
            self._sessions = None
            self._renglo = None

    def _build_graph(self):
        builder = StateGraph(AgentState)

        builder.add_node("load_context", self._load_context)
        builder.add_node("call_llm", self._call_llm)
        builder.add_node("send_response", self._send_response)
        builder.add_node("persist_state", self._persist_state)

        builder.add_edge(START, "load_context")
        builder.add_edge("load_context", "call_llm")
        builder.add_edge("call_llm", "send_response")
        builder.add_edge("send_response", "persist_state")
        builder.add_edge("persist_state", END)

        return builder.compile()

    def _adapter(self) -> RengloAdapter:
        if self._renglo is None:
            raise RuntimeError("RengloAdapter is not initialized for this run")
        return self._renglo

    def _load_context(self, state: AgentState) -> AgentState:
        messages = list(state.get("messages") or [])
        messages.append(
            {
                "role": "user",
                "content": state["inbound_message"],
                "timestamp": self._now(),
            }
        )

        self._adapter().log_event(
            session_id=state["session_id"],
            event_type="inbound_message",
            payload={
                "channel": state.get("channel"),
                "message": state["inbound_message"],
            },
        )

        return {"messages": messages}

    def _call_llm(self, state: AgentState) -> AgentState:
        messages = list(state.get("messages") or [])
        llm_messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful conversational agent running inside Renglo. "
                    "Answer clearly and ask for clarification when needed."
                ),
            },
            *[
                {"role": m["role"], "content": m["content"]}
                for m in messages
                if m.get("role") in {"user", "assistant"}
            ],
        ]

        response_text = self._adapter().call_llm(
            org_id=state["org_id"],
            messages=llm_messages,
            metadata={
                "session_id": state["session_id"],
                "user_id": state.get("user_id"),
                "channel": state.get("channel"),
            },
        )

        messages.append(
            {
                "role": "assistant",
                "content": response_text,
                "timestamp": self._now(),
            }
        )

        self._adapter().log_event(
            session_id=state["session_id"],
            event_type="llm_response",
            payload={"response_text": response_text},
        )

        return {
            "messages": messages,
            "response_text": response_text,
            "should_send": True,
        }

    def _send_response(self, state: AgentState) -> AgentState:
        if not state.get("should_send"):
            return {}

        self._adapter().send_message(
            channel=state.get("channel", "whatsapp"),
            session_id=state["session_id"],
            text=state["response_text"],
            metadata={
                "user_id": state.get("user_id"),
                "org_id": state.get("org_id"),
            },
        )

        self._adapter().log_event(
            session_id=state["session_id"],
            event_type="outbound_message",
            payload={
                "channel": state.get("channel"),
                "message": state["response_text"],
            },
        )

        return {}

    def _persist_state(self, state: AgentState) -> AgentState:
        self._adapter().save_session_state(state["session_id"], dict(state))
        return {}

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
