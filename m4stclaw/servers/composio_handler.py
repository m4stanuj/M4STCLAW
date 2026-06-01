"""
composio_handler.py — Composio Integration Client Bridge
==========================================================
Bridges the M4STCLAW agent engine to Composio's API integration catalog (Linear, Notion, etc.).
"""

import os
import logging
from typing import Dict, Any, Optional

log = logging.getLogger("m4stclaw.servers.composio")

# Flag indicating SDK presence
_composio_available = False
try:
    from composio import ComposioToolSet, Action
    _composio_available = True
except ImportError:
    log.warning("composio module is not installed. Third-party integrations will run in simulation mode.")

def run_composio_action(action_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Executes a Composio action using its SDK and authentication management."""
    result = {
        "status": "error",
        "action": action_name,
        "response": "",
        "mode": "simulation"
    }
    
    api_key = os.getenv("COMPOSIO_API_KEY", "").strip()
    
    # 1. Verify availability and configurations
    if not _composio_available or not api_key:
        log.warning("Composio SDK or COMPOSIO_API_KEY is missing. Simulating execution.")
        result["response"] = (
            f"[SIMULATED COMPOSIO ACTION: {action_name}]\n"
            f"Parameters: {parameters}\n"
            f"Status: Success (Simulation)\n"
            f"Reason: To run real integrations (Notion, Slack, Linear), install the SDK using 'pip install composio-core' "
            f"and set COMPOSIO_API_KEY in your .env configuration file."
        )
        result["status"] = "success"
        return result
        
    # 2. Run active integration via SDK
    try:
        log.info(f"Executing Composio Action: {action_name} with params: {parameters}")
        toolset = ComposioToolSet(api_key=api_key)
        
        # Resolve action reference from string name
        action = Action(action_name)
        
        # Execute tool call
        execution = toolset.execute_action(action=action, params=parameters)
        
        result["response"] = str(execution)
        result["status"] = "success"
        result["mode"] = "sdk"
        
    except Exception as e:
        log.error(f"Composio action '{action_name}' execution failed: {e}")
        result["response"] = f"ERROR: Composio action execution failed. Details: {e}"
        
    return result
