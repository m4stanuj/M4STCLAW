# M4STCLAW Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    M4STCLAW v3.6.0 Architecture                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User Request ──► Task Router ──► Chain Selection               │
│                       │                                         │
│             ┌─────────┼─────────────┐                           │
│             ▼         ▼             ▼                           │
│         Speed     Reasoning       Code    ... 6 more chains     │
│        Cerebras   DeepSeek-R1   DeepSeek                        │
│           │           │            │                            │
│       ┌───┴───┐  ┌────┴───┐  ┌────┴────┐                       │
│       Groq  SN   Gemini OR  OR  Qwen                           │
│      (fallback) (fallback) (fallback)                           │
│                                                                 │
│  ◄── Semantic Cache (Jaccard 0.82+ threshold, 3600s TTL) ──►   │
│  ◄── 3-Tier Memory (Working → Episodic → Semantic)         ──►  │
│  ◄── 18 MCP Tools (Shell, Browser, Vision, Pentest, etc.) ──►  │
└─────────────────────────────────────────────────────────────────┘
```

## Core Module Map

```
m4stclaw/
├── core/
│   ├── config.py       # .env loader, key rotation, cooldowns (thread-safe)
│   ├── router.py       # 9-chain task classifier (word-boundary regex)
│   ├── fallback.py     # Multi-provider LLM fallback loop (httpx)
│   ├── cache.py        # Semantic fuzzy cache (Jaccard similarity)
│   └── memory.py       # 3-tier: Working(T1) + Episodic(T2) + Semantic(T3)
├── servers/
│   ├── server_definitions.py  # Unified FastMCP server (18 tools)
│   ├── shell_handler.py       # Sandboxed command execution
│   ├── browser_handler.py     # Playwright + HTTP fallback
│   ├── vision_handler.py      # OCR + Gemini/Ollama multimodal
│   ├── scrapling_handler.py   # Anti-bot web scraper
│   ├── pentest_handler.py     # Nmap/Nuclei/Shodan (scope-locked)
│   └── composio_handler.py    # Third-party integrations bridge
├── ui/
│   ├── app_server.py          # FastAPI coordinator + MCP mount
│   └── static/                # Dashboard HTML/CSS/JS
└── start.py                   # System launcher
```

## MCP Tool Registry

| Tool Name              | Handler          | Description                              |
|------------------------|------------------|------------------------------------------|
| `router_classify`      | router           | Classify prompt into task chain          |
| `router_status`        | config           | Show key rotation/cooldown status        |
| `llm_query`            | fallback + cache | Execute LLM query with auto-routing     |
| `memory_get_session`   | memory T1        | Read working memory                      |
| `memory_set_session`   | memory T1        | Write working memory                     |
| `memory_add_episodic`  | memory T2        | Record task execution log                |
| `memory_search_episodic` | memory T2      | Search cross-session logs                |
| `memory_add_semantic`  | memory T3        | Store permanent embedding                |
| `memory_query_semantic` | memory T3       | Query semantic memory                    |
| `shell_execute`        | shell            | Run sandboxed system command             |
| `browser_visit`        | browser          | Navigate, interact, screenshot           |
| `vision_analyze`       | vision           | OCR + multimodal image analysis          |
| `scrapling_fetch`      | scrapling        | Anti-bot web content extraction          |
| `pentest_nmap`         | pentest          | Port scan (scope-restricted)             |
| `pentest_nuclei`       | pentest          | Vulnerability template scan              |
| `pentest_shodan`       | pentest          | Shodan IP reconnaissance                 |
| `composio_action`      | composio         | Execute Composio integration             |

## Task Chain Routing

| Chain      | Primary Provider     | Fallback Chain                    |
|------------|---------------------|-----------------------------------|
| Speed      | Cerebras llama-3.3  | Groq → Gemini → OpenRouter → Together |
| Reasoning  | DeepSeek R1         | Gemini → OpenRouter → Together    |
| Code       | DeepSeek Chat       | OpenRouter → SambaNova → Groq → Ollama |
| Vision     | Gemini 2.5 Flash    | OpenRouter                        |
| Research   | DeepSeek R1         | Gemini → OpenRouter → Together    |
| Agent      | DeepSeek R1         | Gemini → Groq → Ollama           |
| Write      | Cerebras            | Groq → Together → OpenRouter      |
| Pentest    | Groq                | DeepSeek R1 → Together            |
| Offline    | Ollama (local)      | —                                 |

## Security Model

- **Shell**: Binary allow-list + command injection prevention (no `;`, `&&`, `|`, `` ` ``, `$(`)
- **Pentest**: Strict IP/domain whitelist (localhost-only by default)
- **Browser**: Screenshot filename sanitization (`os.path.basename`)
- **API Server**: CORS restricted to `localhost:8000`, listens on `127.0.0.1` only
- **Keys**: Never logged, stored only in local `.env`, masked in UI

## Data Flow

1. User sends natural language request via dashboard or MCP client
2. Task Router classifies intent using word-boundary keyword matching
3. Best provider chain selected from 9 available pipelines
4. Semantic cache checked (Jaccard similarity ≥ 0.82)
5. If cache miss, LLM processes with automatic provider failover
6. Response cached with configurable TTL (default: 3600s)
7. Episodic memory (T2) records the task execution log
8. Working memory (T1) stores session context for follow-up queries
