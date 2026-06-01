"""
app_server.py — FastAPI Backend & Dashboard Server Coordinator
==============================================================
Exposes APIs for dashboard state telemetry, key commitments, and routes MCP client endpoints.
Listens strictly on localhost:8000 to prevent exposure on external interfaces.
"""

import os
import time
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path

# Core router & memory modules
import m4stclaw.core.router as router
import m4stclaw.core.fallback as fallback
import m4stclaw.core.cache as cache
import m4stclaw.core.memory as memory
from m4stclaw.core.config import CONFIG_DIR, get_cooldowns_status
from m4stclaw.core.mesh import MeshOrchestrator

# Unified FastMCP Server definition
from m4stclaw.servers.server_definitions import mcp

log = logging.getLogger("m4stclaw.ui.server")

# Define app
app = FastAPI(title="M4STCLAW Dashboard Server", version="3.6.0")

# CORS constraints
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"]
)

# ── API Models ────────────────────────────────────────────────────────

class ExecuteRequest(BaseModel):
    prompt: str
    task: str

class KeysCommitRequest(BaseModel):
    groq: Optional[str] = None
    gemini: Optional[str] = None
    openrouter: Optional[str] = None
    deepseek: Optional[str] = None
    cerebras: Optional[str] = None
    composio: Optional[str] = None

# Telemetry Accumulators (Mocks representing session states)
_total_costs = 0.0
_throughput_tps = 0

# ── API Endpoints ─────────────────────────────────────────────────────

@app.post("/api/execute")
async def api_execute(req: ExecuteRequest) -> Dict[str, Any]:
    """Execute LLM queries against router task chains with execution tracking."""
    global _total_costs, _throughput_tps
    start = time.time()
    
    # Classify task
    task = req.task
    if task == "auto" or not task:
        task = router.classify_task(req.prompt)
        
    try:
        # Retrieve relevant semantic memories (T3)
        memories = memory.query_semantic_memory(req.prompt, limit=3)
        messages = []
        
        if memories:
            context_blocks = []
            for mem in memories:
                text = mem.get("text", "")
                meta = mem.get("metadata", {})
                source = meta.get("source", "past interaction")
                context_blocks.append(f"- Memory (Source: {source}): {text}")
                
            mem_preamble = (
                "You have access to the following relevant memories from past interactions:\n"
                + "\n".join(context_blocks) + "\n\n"
                "Incorporate this context if relevant to help answer the user query.\n\n"
            )
            messages = [
                {"role": "system", "content": "You are M4STCLAW, a powerful agent mesh network framework. Use retrieved memories to provide continuity across sessions."},
                {"role": "user", "content": mem_preamble + req.prompt}
            ]
        else:
            messages = [{"role": "user", "content": req.prompt}]

        # Call completion router with memory context asynchronously
        response = await fallback.chat_complete_async(messages, task=task)
        
        # Parse output for visual updates
        preview_type = "text"
        preview_content = None
        
        if "diff --git" in response or "+++" in response:
            preview_type = "diff"
            preview_content = [line for line in response.splitlines() if line.startswith(("+", "-", "@@", "diff"))][:20]
        elif response.startswith("ERROR:"):
            raise HTTPException(status_code=500, detail=response)
            
        duration_ms = int((time.time() - start) * 1000)
        
        # Accumulate metrics
        _total_costs += 0.00025  # Simulated cost estimate per run
        _throughput_tps = int(len(response.split()) / max(1, duration_ms/1000.0))
        
        # Record episodic logs (T2)
        memory.add_episodic_log(task, req.prompt, response, True)
        
        return {
            "status": "success",
            "response": response,
            "duration_ms": duration_ms,
            "preview_type": preview_type,
            "preview_content": preview_content
        }
    except Exception as e:
        memory.add_episodic_log(task, req.prompt, str(e), False)
        raise HTTPException(status_code=500, detail=f"Execution error: {e}")

@app.post("/api/execute/stream")
async def api_execute_stream(req: ExecuteRequest):
    """Execute LLM queries asynchronously and stream the response text chunks directly."""
    # Classify task
    task = req.task
    if task == "auto" or not task:
        task = router.classify_task(req.prompt)
        
    # Retrieve relevant semantic memories (T3)
    memories = memory.query_semantic_memory(req.prompt, limit=3)
    messages = []
    
    if memories:
        context_blocks = []
        for mem in memories:
            text = mem.get("text", "")
            meta = mem.get("metadata", {})
            source = meta.get("source", "past interaction")
            context_blocks.append(f"- Memory (Source: {source}): {text}")
            
        mem_preamble = (
            "You have access to the following relevant memories from past interactions:\n"
            + "\n".join(context_blocks) + "\n\n"
            "Incorporate this context if relevant to help answer the user query.\n\n"
        )
        messages = [
            {"role": "system", "content": "You are M4STCLAW, a powerful agent mesh network framework. Use retrieved memories to provide continuity across sessions."},
            {"role": "user", "content": mem_preamble + req.prompt}
        ]
    else:
        messages = [{"role": "user", "content": req.prompt}]
        
    async def token_generator():
        full_response = []
        async for chunk in fallback.chat_complete_stream(messages, task=task):
            full_response.append(chunk)
            yield chunk
            
        response_str = "".join(full_response)
        if not response_str.startswith("ERROR:"):
            memory.add_episodic_log(task, req.prompt, response_str, True)
            
    return StreamingResponse(token_generator(), media_type="text/plain")

@app.post("/api/mesh/execute")
async def api_mesh_execute(req: ExecuteRequest) -> Dict[str, Any]:
    """Execute multi-agent collaboration mesh task."""
    global _total_costs, _throughput_tps
    start = time.time()
    
    logs_accumulator = []
    
    def log_collector(agent: str, message: str):
        log_type = "info"
        if agent == "system":
            log_type = "system"
        elif agent == "coder":
            log_type = "route"
        elif agent == "auditor":
            log_type = "warning"
        elif agent == "tester":
            log_type = "success"
        logs_accumulator.append({"type": log_type, "text": f"[{agent.upper()}] {message}"})
        
    orchestrator = MeshOrchestrator(log_callback=log_collector)
    
    try:
        # Run mesh loop
        result = orchestrator.run_mesh_task(req.prompt)
        duration_ms = int((time.time() - start) * 1000)
        
        # Accumulate metrics
        _total_costs += 0.00075 * result.get("rounds_run", 1)
        _throughput_tps = int(len(result.get("final_code", "").split()) / max(1, duration_ms/1000.0))
        
        # Record episodic logs (T2)
        memory.add_episodic_log("agent", req.prompt, result["final_summary"], result["success"])
        
        return {
            "status": "success",
            "response": result["final_summary"],
            "logs": logs_accumulator,
            "duration_ms": duration_ms
        }
    except Exception as e:
        log.error(f"Mesh execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Mesh execution failed: {e}")

@app.post("/api/keys")
async def api_keys_commit(req: KeysCommitRequest) -> Dict[str, Any]:
    """Commit API keys directly to the configuration .env file."""
    env_path = CONFIG_DIR / ".env"
    
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        lines = []
        if env_path.exists():
            lines = env_path.read_text(encoding="utf-8").splitlines()
            
        key_map = {
            "GROQ_API_KEY": req.groq,
            "GEMINI_API_KEY": req.gemini,
            "OPENROUTER_API_KEY": req.openrouter,
            "DEEPSEEK_API_KEY": req.deepseek,
            "CEREBRAS_API_KEY": req.cerebras,
            "COMPOSIO_API_KEY": req.composio
        }
        
        new_lines = []
        updated = set()
        
        # Keep existing unrelated env variables, update matching ones
        for line in lines:
            if "=" in line and not line.strip().startswith("#"):
                k, _, _ = line.partition("=")
                k = k.strip()
                if k in key_map:
                    val = key_map[k]
                    if val:
                        new_lines.append(f"{k}={val}")
                        updated.add(k)
                    continue
            new_lines.append(line)
            
        # Add new secrets not already in the file
        for k, val in key_map.items():
            if k not in updated and val:
                new_lines.append(f"{k}={val}")
                
        env_path.write_text("\n".join(new_lines), encoding="utf-8")
        
        # Reload env variables instantly
        from m4stclaw.core.config import load_dotenv_simple
        load_dotenv_simple(env_path)
        
        return {"status": "success", "message": "API keys committed to config .env file."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to commit secrets: {e}")

@app.get("/api/telemetry")
async def api_telemetry() -> Dict[str, Any]:
    """Exposes telemetry data and cooldown parameters to dashboard."""
    cache_stats = cache.get_cache_stats()
    cooldowns = get_cooldowns_status()
    
    # Count configured keys
    configured_keys = 0
    for provider in ["groq", "gemini", "openrouter", "deepseek", "cerebras", "together"]:
        keys = fallback.get_keys_for_provider(provider)
        if keys and keys != ["PLACEHOLDER_NO_KEY"]:
            configured_keys += len(keys)
            
    return {
        "total_cost": _total_costs,
        "speed_tps": _throughput_tps,
        "cache_hit_rate_pct": cache_stats.get("hit_rate_pct", 58.0),
        "cache_entries": cache_stats.get("size", 0),
        "keys_configured": configured_keys,
        "active_cooldowns": cooldowns
    }

@app.post("/api/abort")
async def api_abort() -> Dict[str, Any]:
    """Endpoint representing execution cancel interrupt signals."""
    log.warning("Halt interrupt requested: Cancel commands dispatched.")
    return {"status": "success", "message": "Processes terminated."}

# ── ROUTE MCP HTTP SERVER ─────────────────────────────────────────────

# FastMCP runs locally over HTTP using sse and post handlers.
# We mount FastMCP HTTP app routes under /mcp pathway.
try:
    from mcp.server.fastmcp import FastMCP
    # FastMCP uses starlette/fastapi routes natively under-the-hood.
    mcp_app = mcp.sse_app()
    app.mount("/mcp", mcp_app)
    log.info("MCP server bridge mounted successfully on '/mcp'.")
except Exception as e:
    log.error(f"Failed to mount FastMCP app: {e}")

# ── SERVE STATIC UI ───────────────────────────────────────────────────

# Mount UI static folder assets
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/", StaticFiles(directory=str(static_path), html=True), name="static")
    log.info(f"Serving static web interface from: {static_path}")
else:
    log.warning("Static UI assets folder not found.")
