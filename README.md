<div align="center">

# 🧠 M4STCLAW v3 — Autonomous AI Mesh Network

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-Native-00E5FF?style=flat-square)](https://modelcontextprotocol.io)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)]()

**A modular, zero-cost autonomous AI framework with 16 MCP servers, 9 intelligent task chains, and multi-provider failover routing.**

[Architecture](#architecture) · [Features](#features) · [Quick Start](#quick-start) · [Task Chains](#task-chains) · [Contributing](#contributing)

</div>

---

## 🔥 What is M4STCLAW?

M4STCLAW is a **Model Context Protocol (MCP)** native AI orchestration framework that dynamically routes tasks across 25+ AI providers using 56 rotating API keys — achieving **100% uptime at $0 cost**.

Instead of relying on a single expensive model, M4STCLAW acts as an **AI mesh network** — automatically selecting the best model for each specific task type, with instant failover if any provider rate-limits.

```
┌─────────────────────────────────────────────────────┐
│                   M4STCLAW v3                       │
│                                                     │
│   User Query ──► Task Router ──► Chain Selection    │
│                      │                              │
│            ┌─────────┼─────────┐                    │
│            ▼         ▼         ▼                    │
│        Speed     Reasoning    Code                  │
│       Cerebras    Kimi K2   MiMo-V2                │
│         │           │          │                    │
│     ┌───┴───┐  ┌────┴───┐ ┌───┴────┐              │
│     Groq  SN   DS-R1 Nem  Qwen3 K2               │
│     (fallback) (fallback) (fallback)               │
│                                                     │
│   ◄── Semantic Cache (3600s TTL, 40-60% savings) ──►│
│   ◄── 3-Tier Memory (Working→Episodic→Semantic)  ──►│
└─────────────────────────────────────────────────────┘
```

## ✨ Features

### 🔀 Intelligent Multi-Provider Routing
- **9 specialized task chains**: Speed, Reasoning, Code, Vision, Research, Agent, Write, Pentest, Offline
- **56 rotating API keys** across 7 providers (Groq, Gemini, OpenRouter, Cerebras, SambaNova, DeepSeek, Together)
- **Automatic failover**: If primary model rate-limits, fallback fires in <100ms

### 🧠 3-Tier Memory Architecture
| Tier | Type | Backend | Use Case |
|------|------|---------|----------|
| T1 | Working Memory | JSON State | Current session context |
| T2 | Episodic Memory | JSON Logs | Cross-session task history |
| T3 | Semantic Memory | ChromaDB | Permanent vector embeddings |

### 🛡️ Offensive Security Integration (CAI Layer)
- Automated **Nmap** port scanning
- **Nuclei** vulnerability detection
- **Shodan** reconnaissance
- **CVE** database lookups
- Session-based pentest workflows with auto-generated reports

### 👁️ 5-Layer Vision Engine
1. **OpenCV** — Computer vision preprocessing
2. **Tesseract** — OCR text extraction
3. **Windows UIA** — Desktop UI automation
4. **Ollama (Local)** — Offline image understanding
5. **Gemini 2.5 Flash** — Cloud multimodal analysis

### 🔌 16 MCP Servers
```
task_router    │ universal_bridge │ pentest      │ m4st_agent
memory         │ research         │ skills       │ react
file           │ shell            │ browser      │ vision
notify         │ scrapling        │ llm_fallback │ _mcp_base
```

## 🏗️ Architecture

```mermaid
graph TB
    A[User Input] --> B[Task Router MCP]
    B --> C{Task Classification}
    C -->|Speed| D[Cerebras Chain]
    C -->|Reasoning| E[Kimi K2 Chain]
    C -->|Code| F[MiMo-V2 Chain]
    C -->|Vision| G[Gemini 2.5 Chain]
    C -->|Pentest| H[DeepSeek-R1 Chain]
    D & E & F & G & H --> I[Semantic Cache]
    I --> J[3-Tier Memory]
    J --> K[Response]
```

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/m4stanuj/M4STCLAW.git
cd M4STCLAW

# Copy environment template
cp .env.template .env
# Edit .env with your API keys

# Install dependencies
pip install -r requirements.txt

# Launch
python start.bat
```

## 📊 Performance

| Metric | Value |
|--------|-------|
| Avg Response Time | ~1.2s (cached: ~0.3s) |
| API Cost | $0/month |
| Uptime | 99.9%+ (multi-provider failover) |
| Cache Hit Rate | 40-60% on repeated queries |
| Memory Recall | Semantic search across all sessions |

## 🗺️ Roadmap

- [x] MCP-native architecture
- [x] 16 specialized MCP servers
- [x] Multi-provider routing (56 keys)
- [x] 3-tier memory system
- [x] Offensive security integration
- [x] 5-layer vision pipeline
- [ ] Multi-agent collaboration (OMO protocol)
- [ ] Web dashboard for monitoring
- [ ] Plugin marketplace

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">
  <sub>Built with obsession by <a href="https://github.com/m4stanuj">M4ST</a> · Solo Developer · Zero Funding · Infinite Iteration</sub>
</div>
