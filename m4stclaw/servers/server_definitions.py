"""
server_definitions.py — Unified FastMCP Server Definitions
============================================================
Defines and registers all M4STCLAW MCP tools under a single fastmcp client server.
"""

import json
import logging
from typing import Optional, Dict, Any
from mcp.server.fastmcp import FastMCP

# Core router & memory modules
import m4stclaw.core.router as router
import m4stclaw.core.fallback as fallback
import m4stclaw.core.cache as cache
import m4stclaw.core.memory as memory

# MCP server handlers
import m4stclaw.servers.shell_handler as shell
import m4stclaw.servers.browser_handler as browser
import m4stclaw.servers.vision_handler as vision
import m4stclaw.servers.scrapling_handler as scrapling
import m4stclaw.servers.pentest_handler as pentest
import m4stclaw.servers.composio_handler as composio

log = logging.getLogger("m4stclaw.servers.definitions")

# Create unified server instance
mcp = FastMCP(
    "m4stclaw_mesh_server",
    instructions=(
        "M4STCLAW Mesh Server: Unified control center exposing routing, memory, shell commands, "
        "browser crawls, screen OCR, anti-bot web scraping, security scans, and Composio tools."
    )
)

# ═══════════════════════════════════════════════════════════════
# TASK ROUTING TOOLS
# ═══════════════════════════════════════════════════════════════

@mcp.tool(name="router_classify")
def router_classify(prompt: str) -> str:
    """Classifies a user query into one of the 9 specialized task chains (speed, reasoning, code, etc.)."""
    return router.classify_task(prompt)

@mcp.tool(name="router_status")
def router_status() -> str:
    """Returns the rotation and cooldown status of configured provider API keys."""
    status = fallback.get_cooldowns_status()
    if not status:
        return "All API keys are active and cooled down."
    return json.dumps({"active_cooldowns_sec": status}, indent=2)

@mcp.tool(name="llm_query")
def llm_query(prompt: str, task: str = "speed", use_cache: bool = True) -> str:
    """Queries the optimal LLM task chain with automatic provider fallback routing."""
    if use_cache:
        cached = cache.get_cached_response(prompt)
        if cached:
            return cached
            
    response = fallback.chat_complete([{"role": "user", "content": prompt}], task=task)
    
    if use_cache and not response.startswith("ERROR:"):
        cache.set_cached_response(prompt, response)
        
    return response

# ═══════════════════════════════════════════════════════════════
# 3-TIER MEMORY TOOLS
# ═══════════════════════════════════════════════════════════════

@mcp.tool(name="memory_get_session")
def memory_get_session(key: str) -> str:
    """Gets a value from current working memory (T1)."""
    val = memory.get_working_value(key)
    return str(val) if val is not None else "Key not found."

@mcp.tool(name="memory_set_session")
def memory_set_session(key: str, value: str) -> str:
    """Sets a value in the current working memory (T1)."""
    memory.set_working_value(key, value)
    return f"Key '{key}' set to '{value}'."

@mcp.tool(name="memory_add_episodic")
def memory_add_episodic(task_type: str, query: str, response: str, success: bool = True) -> str:
    """Records a task execution log into episodic memory (T2)."""
    memory.add_episodic_log(task_type, query, response, success)
    return "Episodic task log recorded."

@mcp.tool(name="memory_search_episodic")
def memory_search_episodic(keyword: str, limit: int = 5) -> str:
    """Searches cross-session episodic memory logs (T2) for matching keywords."""
    logs = memory.search_episodic_logs(keyword=keyword, limit=limit)
    return json.dumps(logs, indent=2)

@mcp.tool(name="memory_add_semantic")
def memory_add_semantic(text: str, metadata_json: Optional[str] = None) -> str:
    """Stores a permanent document embedding into ChromaDB semantic memory (T3)."""
    metadata = {}
    if metadata_json:
        try:
            metadata = json.loads(metadata_json)
        except Exception as e:
            return f"ERROR: Invalid JSON metadata: {e}"
            
    memory.add_semantic_memory(text, metadata)
    return "Semantic document memory embedded successfully."

@mcp.tool(name="memory_query_semantic")
def memory_query_semantic(query_text: str, limit: int = 3) -> str:
    """Queries ChromaDB semantic memory (T3) for relevant context."""
    results = memory.query_semantic_memory(query_text, limit=limit)
    return json.dumps(results, indent=2)

# ═══════════════════════════════════════════════════════════════
# EXECUTION & SERVICE TOOLS
# ═══════════════════════════════════════════════════════════════

@mcp.tool(name="shell_execute")
def shell_execute(command: str, cwd: str = ".") -> str:
    """Executes developer system commands securely within the sandbox boundary."""
    return shell.execute_command(command, cwd)

@mcp.tool(name="browser_visit")
def browser_visit(url: str, click_selector: Optional[str] = None, screenshot_name: Optional[str] = None) -> str:
    """Navigates to websites, interacts with elements, and captures screenshots using Playwright."""
    res = browser.visit_webpage(url, click_selector, screenshot_name)
    return json.dumps(res, indent=2)

@mcp.tool(name="vision_analyze")
def vision_analyze(prompt: str, image_path: Optional[str] = None, use_ollama: bool = False) -> str:
    """Captures and analyzes display monitor screenshots with OCR and multimodal vision model routes."""
    res = vision.analyze_image(prompt, image_path, use_ollama)
    return json.dumps(res, indent=2)

@mcp.tool(name="scrapling_fetch")
def scrapling_fetch(url: str) -> str:
    """Performs an anti-bot static crawl of raw text contents from target URLs."""
    res = scrapling.extract_clean_web_text(url)
    return json.dumps(res, indent=2)

# ═══════════════════════════════════════════════════════════════
# SECURITY & INTEGRATION TOOLS
# ═══════════════════════════════════════════════════════════════

@mcp.tool(name="pentest_nmap")
def pentest_nmap(target: str, ports: str = "80,443,8000,8080") -> str:
    """Runs a port scan against a whitelisted in-scope local target."""
    return pentest.run_nmap_scan(target, ports)

@mcp.tool(name="pentest_nuclei")
def pentest_nuclei(target: str, template: str = "http/technologies") -> str:
    """Runs nuclei vulnerability checks against a whitelisted local target."""
    return pentest.run_nuclei_templates(target, template)

@mcp.tool(name="pentest_shodan")
def pentest_shodan(ip: str) -> str:
    """Queries Shodan for public information about the host IP."""
    return pentest.get_shodan_host_info(ip)

@mcp.tool(name="composio_action")
def composio_action(action_name: str, parameters_json: str) -> str:
    """Executes a Composio action (connects to Slack, Linear, Notion, Jira) with parameters."""
    try:
        params = json.loads(parameters_json)
    except Exception as e:
        return f"ERROR: Invalid parameters JSON: {e}"
        
    res = composio.run_composio_action(action_name, params)
    return json.dumps(res, indent=2)
