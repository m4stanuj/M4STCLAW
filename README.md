<div align="center">

# ⚡ M4STCLAW v3.6.0 — Autonomous AI Mesh Network

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![CI](https://github.com/m4stanuj/M4STCLAW/actions/workflows/ci.yml/badge.svg)](https://github.com/m4stanuj/M4STCLAW/actions)
[![Release](https://img.shields.io/github/v/release/m4stanuj/M4STCLAW?style=flat-square&color=3b82f6)](https://github.com/m4stanuj/M4STCLAW/releases)
[![Stars](https://img.shields.io/github/stars/m4stanuj/M4STCLAW?style=flat-square&color=f59e0b)](https://github.com/m4stanuj/M4STCLAW/stargazers)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/m4stanuj/M4STCLAW?style=flat-square)](https://github.com/m4stanuj/M4STCLAW/commits)
[![MCP](https://img.shields.io/badge/MCP-Native-8b5cf6?style=flat-square)](https://modelcontextprotocol.io)

**Zero-cost AI framework with 18 MCP tools, 9 intelligent task chains, multi-provider failover routing, and a 3-tier memory architecture.**

[Architecture](#-architecture) · [Features](#-features) · [Quick Start](#-quick-start) · [Task Chains](#-task-chain-routing) · [Contributing](#-contributing)

</div>

---

## What is M4STCLAW?

M4STCLAW is a **Model Context Protocol (MCP)** native AI orchestration framework that dynamically routes tasks across multiple AI providers using rotating API keys — achieving **near-100% uptime at $0 cost**.

Instead of relying on a single expensive model, M4STCLAW acts as an **AI mesh network** — automatically selecting the best model for each task type, with instant failover if any provider rate-limits.

```
┌─────────────────────────────────────────────────────┐
│                  M4STCLAW v3.6.0                    │
│                                                     │
│   User Query ──► Task Router ──► Chain Selection    │
│                      │                              │
│            ┌─────────┼─────────┐                    │
│            ▼         ▼         ▼                    │
│        Speed     Reasoning    Code    ... 6 more    │
│       Cerebras   DeepSeek-R1 DeepSeek               │
│         │           │          │                    │
│     ┌───┴───┐  ┌────┴───┐ ┌───┴────┐              │
│     Groq  SN   Gemini OR  OR  Qwen                 │
│     (fallback) (fallback) (fallback)                │
│                                                     │
│   ◄── Semantic Cache (3600s TTL, ~58% hit rate) ──► │
│   ◄── 3-Tier Memory (Working→Episodic→Semantic)  ──►│
│   ◄── 18 MCP Tools (Shell/Browser/Vision/Pentest)──►│
└─────────────────────────────────────────────────────┘
```

## ✨ Features

### 🔀 Intelligent Multi-Provider Routing
- **9 specialized task chains**: Speed, Reasoning, Code, Vision, Research, Agent, Write, Pentest, Offline
- **Rotating API keys** across 7+ providers (Groq, Gemini, OpenRouter, Cerebras, SambaNova, DeepSeek, Together)
- **Smart key detection** — paste any key prefixed with `gsk_`, `AIza`, `sk-or-`, etc. and it auto-routes to the right provider
- **Automatic failover** — if primary model rate-limits, fallback fires in <100ms

### 🧠 3-Tier Memory Architecture

| Tier | Type | Backend | Purpose |
|------|------|---------|---------|
| T1 | Working Memory | In-RAM JSON | Current session context |
| T2 | Episodic Memory | JSON on disk | Cross-session task history |
| T3 | Semantic Memory | ChromaDB / JSON fallback | Permanent vector embeddings |

### 🛡️ Security Integration (CAI Layer)
- **Nmap** port scanning (scope-restricted to localhost)
- **Nuclei** vulnerability template detection
- **Shodan** IP reconnaissance
- Strict target whitelist enforcement — no external scanning without explicit authorization

### 👁️ Vision Engine
- **Tesseract OCR** — text extraction from screenshots
- **Gemini 2.5 Flash** — cloud multimodal analysis
- **Ollama LLaVA** — offline local image understanding
- **Pillow** — automated screen capture

### 🔌 18 MCP Tools

| Category | Tools |
|----------|-------|
| **Routing** | `router_classify`, `router_status`, `llm_query` |
| **Memory** | `memory_get_session`, `memory_set_session`, `memory_add_episodic`, `memory_search_episodic`, `memory_add_semantic`, `memory_query_semantic` |
| **Execution** | `shell_execute`, `browser_visit`, `vision_analyze`, `scrapling_fetch` |
| **Security** | `pentest_nmap`, `pentest_nuclei`, `pentest_shodan` |
| **Integration** | `composio_action` |

### 📊 Web Dashboard
Enterprise-grade admin panel served on `localhost:8000`:
- Real-time telemetry (cost, throughput, cache stats)
- Interactive AI console with chain selection
- Provider status table with health monitoring
- API key configuration manager
- Live task routing DAG visualization
- Activity log console

## 🏗️ Architecture

```
m4stclaw/
├── core/
│   ├── config.py       # .env loader, key rotation, cooldowns
│   ├── router.py       # 9-chain task classifier
│   ├── fallback.py     # Multi-provider LLM fallback loop
│   ├── cache.py        # Semantic fuzzy cache (Jaccard similarity)
│   └── memory.py       # 3-tier memory engine
├── servers/
│   ├── server_definitions.py  # Unified FastMCP server (18 tools)
│   ├── shell_handler.py       # Sandboxed command execution
│   ├── browser_handler.py     # Playwright + HTTP fallback
│   ├── vision_handler.py      # OCR + multimodal vision
│   ├── scrapling_handler.py   # Anti-bot web scraper
│   ├── pentest_handler.py     # Nmap/Nuclei/Shodan
│   └── composio_handler.py    # Third-party integrations
├── ui/
│   ├── app_server.py          # FastAPI + MCP mount
│   └── static/                # Dashboard (HTML/CSS/JS)
├── start.py                   # System launcher
└── setup.py                   # Package configuration
```

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/m4stanuj/M4STCLAW.git
cd M4STCLAW

# Configure
cp .env.template .env
# Edit .env with your API keys

# Install
pip install -r requirements.txt

# Launch
python start.py
```

Dashboard opens at **http://localhost:8000** • MCP endpoint at **http://localhost:8000/mcp**

### Installation Options

```bash
# Minimal (core routing only)
pip install -r requirements.txt

# Full (ChromaDB, Playwright, OCR, Composio)
pip install -e ".[full]"

# Development (includes testing tools)
pip install -e ".[dev]"
```

## 🔀 Task Chain Routing

| Chain | Primary | Fallbacks | Best For |
|-------|---------|-----------|----------|
| **Speed** | Cerebras | Groq → Gemini → OpenRouter → Together | Quick answers, translations |
| **Reasoning** | DeepSeek R1 | Gemini → OpenRouter → Together | Logic, math, analysis |
| **Code** | DeepSeek | OpenRouter → SambaNova → Groq → Ollama | Programming, debugging |
| **Vision** | Gemini 2.5 | OpenRouter | Image analysis, OCR |
| **Research** | DeepSeek R1 | Gemini → OpenRouter → Together | Deep dives, trends |
| **Agent** | DeepSeek R1 | Gemini → Groq → Ollama | Workflow automation |
| **Write** | Cerebras | Groq → Together → OpenRouter | Essays, docs, emails |
| **Pentest** | Groq | DeepSeek R1 → Together | Security analysis |
| **Offline** | Ollama | — | No internet, local only |

## 📊 Performance

| Metric | Value |
|--------|-------|
| Avg Response Time | ~1.2s (cached: ~0.3s) |
| API Cost | $0/month (free-tier routing) |
| Cache Hit Rate | ~58% on production workloads |
| Provider Failover | <100ms automatic switchover |
| Memory Tiers | 3 (Working → Episodic → Semantic) |
| MCP Tools | 18 registered endpoints |

## 🔒 Security

- **Shell execution**: Binary allow-list + command injection prevention
- **Pentest scanning**: Strict localhost-only whitelist (configurable via `M4STCLAW_ALLOWED_SCOPE`)
- **API server**: Listens on `127.0.0.1` only, CORS restricted
- **Key storage**: Local `.env` only, never logged, masked in dashboard
- **Browser screenshots**: Filename sanitization against path traversal
- **DOM manipulation**: Safe `textContent`/`createElement` only (no `innerHTML`)

## 🗺️ Roadmap

- [x] MCP-native architecture (v3.0)
- [x] 18 MCP tool endpoints
- [x] Multi-provider routing with key rotation
- [x] 3-tier memory system (Working + Episodic + Semantic)
- [x] Offensive security integration (Nmap/Nuclei/Shodan)
- [x] Vision pipeline (OCR + Gemini + Ollama)
- [x] Semantic fuzzy cache (Jaccard similarity)
- [x] Enterprise web dashboard
- [x] Composio third-party integration bridge
- [ ] Multi-agent collaboration protocol
- [ ] Docker deployment package
- [ ] Plugin marketplace

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. Pull requests welcome.

```bash
# Run tests
pip install pytest
pytest tests/ -v
```

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
  <sub>Built by <a href="https://github.com/m4stanuj">M4ST</a> · Solo Developer · Zero Funding · Continuous Iteration Since 2023</sub>
</div>
