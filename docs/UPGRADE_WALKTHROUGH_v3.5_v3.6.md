# M4STCLAW v3.5.0 and v3.6.0 Upgrade Walkthrough

This document summarizes the major upgrades, architectural improvements, and security enhancements implemented across M4STCLAW v3.5.0 and v3.6.0.

## M4STCLAW v3.6.0

Async migration, SSE streaming, secure command execution, and TF-IDF vector fallback.

### 1. Secure `shell=False` Command Execution

File: [`m4stclaw/servers/shell_handler.py`](../m4stclaw/servers/shell_handler.py)

- Replaced unsafe `shell=True` subprocess execution with `shell=False`.
- Uses `shlex.split(cmd_str, posix=False)` to preserve Windows path backslashes.
- Resolves binaries dynamically via `shutil.which`.
- Enforces sandbox boundary checks before command execution.
- Handles Windows command prompt built-ins such as `dir` and `echo` through explicit `cmd.exe /c` argument lists instead of raw shell strings.

### 2. Zero-Dependency TF-IDF + Cosine Similarity Memory Fallback

File: [`m4stclaw/core/memory.py`](../m4stclaw/core/memory.py)

- Upgraded fallback semantic memory search from syntax-level Jaccard word intersection to a pure Python TF-IDF + cosine similarity vector space model.
- Calculates Term Frequency, Document Frequency, and Inverse Document Frequency dynamically over the memory catalog.
- Builds normalized document and query vectors.
- Scores candidate memories with cosine similarity and returns top matches by mathematical relevance.

### 3. FastAPI Async Migration and SSE Token Streaming

Files:

- [`m4stclaw/core/fallback.py`](../m4stclaw/core/fallback.py)
- [`m4stclaw/ui/app_server.py`](../m4stclaw/ui/app_server.py)
- [`m4stclaw/ui/static/app.js`](../m4stclaw/ui/static/app.js)

Upgrades:

- Added `chat_complete_async` for async request flows.
- Added `chat_complete_stream` for streaming token/chunk generators.
- Converted dashboard execution endpoints to `async def`.
- Added `/api/execute/stream` using FastAPI `StreamingResponse`.
- Upgraded dashboard chat submission to process raw HTTP chunks through `ReadableStream` reader loops.
- Enables smooth real-time character-by-character output in the dashboard.

## M4STCLAW v3.5.0

Multi-agent mesh orchestration engine.

### 1. Multi-Agent Mesh Engine

File: [`m4stclaw/core/mesh.py`](../m4stclaw/core/mesh.py)

- Implemented stateful coordination between Coder, Auditor, and Tester agents.
- Agents work concurrently through build, audit, and test phases.
- Adds feedback-based iteration instead of one-shot generation.
- Designed for programming tasks where solution quality improves through role separation.

### 2. Dashboard and MCP Mesh Execution

Files:

- [`m4stclaw/ui/app_server.py`](../m4stclaw/ui/app_server.py)
- [`m4stclaw/servers/server_definitions.py`](../m4stclaw/servers/server_definitions.py)

Upgrades:

- Added `/api/mesh/execute` endpoint.
- Registered `mesh_run` as an MCP tool.
- Added execution log callback mapping for dashboard visibility.
- Returns per-agent collaboration traces to the Activity Log console.

## Verification Results

Current verification target: v3.6.0.

- `pytest`: 25 unit tests passing.
- GitHub sync: commits pushed to [`m4stanuj/M4STCLAW`](https://github.com/m4stanuj/M4STCLAW).
- Release tags:
  - `v3.5.0`
  - `v3.6.0`

## Why This Matters

These two releases move M4STCLAW from a synchronous local AI operator into a more durable mesh runtime:

- Safer local command execution.
- Better memory relevance without requiring vector database dependencies.
- Real-time streaming UX.
- Async server flow for better concurrency.
- Multi-agent execution loop for coding tasks.

The key shift is architectural: M4STCLAW is no longer only a routed assistant stack. It now has the foundations of a live multi-agent execution runtime.
