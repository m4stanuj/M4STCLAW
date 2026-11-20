"""
app_server.py — FastAPI Backend & Dashboard Server Coordinator
==============================================================
Serves the local dashboard and its authenticated API.
"""

import asyncio
import os
import time
import logging
import secrets
import re
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel
from pathlib import Path
from dataclasses import dataclass

# Core router & memory modules
import m4stclaw.core.router as router
import m4stclaw.core.fallback as fallback
import m4stclaw.core.cache as cache
import m4stclaw.core.memory as memory
from m4stclaw.core.config import (
    CONFIG_DIR, ManagedProviderKeyError, get_cooldowns_status, update_provider_keys,
)
from m4stclaw.core.mesh import MeshOrchestrator

log = logging.getLogger("m4stclaw.ui.server")

# Define app
app = FastAPI(
    title="M4STCLAW Dashboard Server",
    version="3.6.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

API_TOKEN_ENV = "M4STCLAW_API_TOKEN"


def _configured_api_token() -> str:
    """Return the configured control-plane token without ever logging it."""
    value = os.getenv(API_TOKEN_ENV, "")
    return value if re.fullmatch(r"[A-Za-z0-9_-]{32,128}", value) else ""


@app.middleware("http")
async def require_control_plane_auth(request: Request, call_next):
    """Require a bearer token for every dashboard API endpoint."""
    path = request.url.path
    if path == "/api" or path.startswith("/api/"):
        expected = _configured_api_token()
        if not expected:
            return JSONResponse(
                status_code=503,
                content={"detail": f"{API_TOKEN_ENV} must be configured before the control plane can be used."},
            )
        scheme, _, token = request.headers.get("Authorization", "").partition(" ")
        if scheme.lower() != "bearer" or not secrets.compare_digest(
            token.encode("utf-8"), expected.encode("ascii")
        ):
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required. Use a Bearer token."},
                headers={"WWW-Authenticate": "Bearer"},
            )

    return await call_next(request)


app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1"])

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


@dataclass
class ExecutionTelemetry:
    completed_runs: int = 0
    failed_runs: int = 0
    last_run_duration_ms: Optional[int] = None

    def record(self, start: float, *, succeeded: bool) -> int:
        duration_ms = round((time.perf_counter() - start) * 1000)
        self.last_run_duration_ms = duration_ms
        if succeeded:
            self.completed_runs += 1
        else:
            self.failed_runs += 1
        return duration_ms


app.state.execution_telemetry = ExecutionTelemetry()

# ── API Endpoints ─────────────────────────────────────────────────────

@app.get("/api/auth/check")
async def api_check_auth() -> Dict[str, str]:
    return {"status": "authenticated"}


@app.post("/api/execute")
async def api_execute(req: ExecuteRequest) -> Dict[str, Any]:
    """Execute LLM queries against router task chains with execution tracking."""
    start = time.perf_counter()
    
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
        
        if response.startswith("ERROR:"):
            raise HTTPException(status_code=503, detail="No provider could complete the request.")
        if "diff --git" in response or "+++" in response:
            preview_type = "diff"
            preview_content = [line for line in response.splitlines() if line.startswith(("+", "-", "@@", "diff"))][:20]
        
        # Record episodic logs (T2)
        memory.add_episodic_log(task, req.prompt, response, True)
        duration_ms = app.state.execution_telemetry.record(start, succeeded=True)
        
        return {
            "status": "success",
            "response": response,
            "duration_ms": duration_ms,
            "preview_type": preview_type,
            "preview_content": preview_content
        }
    except HTTPException:
        app.state.execution_telemetry.record(start, succeeded=False)
        raise
    except Exception:
        app.state.execution_telemetry.record(start, succeeded=False)
        log.exception("Dashboard execution failed")
        raise HTTPException(status_code=500, detail="Execution failed.") from None

@app.post("/api/execute/stream")
async def api_execute_stream(req: ExecuteRequest):
    """Execute LLM queries asynchronously and stream the response text chunks directly."""
    start = time.perf_counter()
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
        try:
            async for chunk in fallback.chat_complete_stream(messages, task=task):
                full_response.append(chunk)
                yield chunk
            response_str = "".join(full_response).strip()
            succeeded = bool(response_str) and not response_str.startswith("ERROR:")
            if succeeded:
                memory.add_episodic_log(task, req.prompt, response_str, True)
        except Exception:
            log.exception("Dashboard stream failed")
            app.state.execution_telemetry.record(start, succeeded=False)
            raise
        app.state.execution_telemetry.record(start, succeeded=succeeded)
            
    return StreamingResponse(token_generator(), media_type="text/plain")

@app.post("/api/mesh/execute")
async def api_mesh_execute(req: ExecuteRequest) -> Dict[str, Any]:
    """Execute multi-agent collaboration mesh task."""
    start = time.perf_counter()
    
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
        result = await asyncio.to_thread(orchestrator.run_mesh_task, req.prompt)
        
        # Record episodic logs (T2)
        memory.add_episodic_log("agent", req.prompt, result["final_summary"], result["success"])
        duration_ms = app.state.execution_telemetry.record(start, succeeded=result["success"])
        
        return {
            "status": "success" if result["success"] else "error",
            "response": result["final_summary"],
            "logs": logs_accumulator,
            "duration_ms": duration_ms
        }
    except Exception:
        app.state.execution_telemetry.record(start, succeeded=False)
        log.exception("Mesh execution failed")
        raise HTTPException(status_code=500, detail="Mesh execution failed.") from None

@app.post("/api/keys")
async def api_keys_commit(req: KeysCommitRequest) -> Dict[str, Any]:
    """Save explicitly entered provider keys; blank fields leave existing keys alone."""
    updated = {f"{name.upper()}_API_KEY": value for name, value in req.model_dump().items() if value}
    try:
        count = update_provider_keys(CONFIG_DIR / ".env", updated)
    except ValueError:
        raise HTTPException(status_code=422, detail="Enter a single-line token for each key.") from None
    except ManagedProviderKeyError:
        raise HTTPException(status_code=409, detail="A matching key is managed by the server environment.") from None
    except OSError:
        log.error("Could not save the provider key file.")
        raise HTTPException(status_code=500, detail="Could not save provider keys.") from None
    return {"status": "success", "updated": count}

@app.get("/api/telemetry")
async def api_telemetry() -> Dict[str, Any]:
    """Exposes telemetry data and cooldown parameters to dashboard."""
    cache_stats = cache.get_cache_stats()
    cooldowns = get_cooldowns_status()
    execution = app.state.execution_telemetry
    
    models_by_provider: Dict[str, list[str]] = {}
    for name, _, model, _ in fallback.ALL_PROVIDERS:
        models_by_provider.setdefault(name, []).append(model)

    configured_keys = 0
    providers = []
    for name, models in models_by_provider.items():
        keys = [key for key in fallback.get_keys_for_provider(name) if key != "PLACEHOLDER_NO_KEY"]
        configured_keys += len(keys)
        providers.append({
            "name": name,
            "models": models,
            "local": name == "ollama",
            "configured_keys": len(keys),
            "cooling_keys": sum(f"{name}:{index}" in cooldowns for index in range(len(keys))),
        })
            
    return {
        "completed_runs": execution.completed_runs,
        "failed_runs": execution.failed_runs,
        "last_run_duration_ms": execution.last_run_duration_ms,
        "cache_hit_rate_pct": cache_stats["hit_rate_pct"] if cache_stats["hits"] + cache_stats["misses"] else None,
        "cache_entries": cache_stats.get("size", 0),
        "keys_configured": configured_keys,
        "providers": providers,
        "active_cooldowns": cooldowns
    }

@app.post("/api/abort")
async def api_abort() -> Dict[str, Any]:
    raise HTTPException(status_code=501, detail="Server-side cancellation is unavailable.")

# ── SERVE STATIC UI ───────────────────────────────────────────────────

# Mount UI static folder assets
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/", StaticFiles(directory=str(static_path), html=True), name="static")
    log.info(f"Serving static web interface from: {static_path}")
else:
    log.warning("Static UI assets folder not found.")
