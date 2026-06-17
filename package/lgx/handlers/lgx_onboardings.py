from __future__ import annotations

from typing import Any, Dict, List

from flask import current_app

from renglo.auth.auth_controller import AuthController
from renglo.common import load_config
from renglo.data.data_controller import DataController


class LgxOnboardings:
    """
    Install the LGX tool into an existing portfolio.

    No onboarding blueprint is required — the handler only expects ``portfolio``
    in the payload (same contract as newer extension onboardings).
    """

    def __init__(self) -> None:
        config = load_config()
        self.DAC = DataController(config=config)
        self.AUC = AuthController(config=config)
        self.bridge: Dict[str, Any] = {}

    def create_tool(self, portfolio: str, tool: str, handle: str) -> Dict[str, Any]:
        action = "create_tool"
        current_app.logger.debug("Installing LGX tool in portfolio")

        kwargs = {
            "name": tool,
            "handle": handle,
            "portfolio_id": portfolio,
        }
        response = self.AUC.create_entity("tool", **kwargs)
        self.bridge["tool_id"] = response.get("document", {}).get("_id")

        if not response.get("success"):
            return {
                "success": False,
                "action": action,
                "message": "Could not install tool",
                "input": kwargs,
                "output": response,
            }
        return {
            "success": True,
            "action": action,
            "message": "Tool installed",
            "input": kwargs,
            "output": response,
        }

    def create_schd_tool_doc(self, portfolio: str, org: str, doc: Dict[str, Any]) -> Dict[str, Any]:
        action = "create_schd_tool_doc"
        response, _status = self.DAC.post_a_b(portfolio, org, "schd_tools", doc)
        if not response.get("success"):
            return {
                "success": False,
                "action": action,
                "message": "Could not register schd tool",
                "input": doc,
                "output": response,
            }
        return {
            "success": True,
            "action": action,
            "message": "Scheduler tool registered",
            "input": doc,
            "output": response,
        }

    def refresh_tree(self) -> Dict[str, Any]:
        action = "refresh_tree"
        response = self.AUC.refresh_tree()
        if not response.get("success"):
            return {
                "success": False,
                "action": action,
                "message": "Tree could not be generated",
                "input": [],
                "output": response,
            }
        return {
            "success": True,
            "action": action,
            "message": "The tree has been generated",
            "input": [],
            "output": response,
        }

    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = []

        existing_portfolio = None
        if "portfolio" in payload and payload["portfolio"] != "":
            existing_portfolio = str(payload["portfolio"])

        if not existing_portfolio:
            return {"success": False, "output": "No portfolio selected"}

        response_5 = self.create_tool(existing_portfolio, "LGX", "lgx")
        results.append(response_5)
        if not response_5["success"]:
            return {"success": False, "output": results}

        demo_tool = {
            "key": "demo_lgx_agent",
            "name": "LGX Demo Agent",
            "goal": "Conversational LangGraph agent for LGX chat UI",
            "handler": "lgx/demo_lgx_agent",
            "init": "_",
            "instructions": "Routes inbound chat messages through the LGX LangGraph demo agent.",
            "input": "{\"message\":\"User message text (optional when using chat UI data field)\"}",
            "output": "_",
        }
        response_schd = self.create_schd_tool_doc(existing_portfolio, "_all", demo_tool)
        results.append(response_schd)
        if not response_schd["success"]:
            return {"success": False, "output": results}

        response_11 = self.refresh_tree()
        results.append(response_11)
        if not response_11["success"]:
            return {"success": False, "output": results}

        return {
            "success": True,
            "message": "run completed",
            "input": payload,
            "output": results,
        }
