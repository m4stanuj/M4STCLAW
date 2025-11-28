# Changelog

All notable changes to M4STCLAW are documented here. This project adheres to [Semantic Versioning](https://semver.org/).

## [3.2.1] — 2026-04-18

### Fixed
- Race condition in `task_router` when 3+ agents request same chain simultaneously
- Memory tier promotion failing for entries with non-ASCII characters
- Cerebras chain timeout increased from 8s to 12s to handle complex reasoning

### Changed
- Default semantic cache TTL raised from 1800s to 3600s based on production metrics

## [3.2.0] — 2026-04-02

### Added
- **Kimi K2** integration as primary reasoning model (replaces DeepInfra for chain 2)
- **MiMo-V2** code chain — outperforms Qwen3-Coder on HumanEval (87.2% pass@1)
- DAG-based sub-task orchestration for `agent_ultrawork` pipeline
- Hot-reload for `SOUL.md` — personality changes apply without restart

### Changed
- Provider pool expanded from 48 to 56 rotating API keys
- Upgraded ChromaDB from 0.4.x to 0.5.3 for improved vector recall

### Removed
- Deprecated `openai_direct` chain (migrated to OpenRouter unified endpoint)

## [3.1.0] — 2026-02-14

### Added
- 5-layer vision pipeline: OpenCV → Tesseract → UIA → Ollama → Gemini 2.5 Flash
- Browser automation MCP server (Playwright-based headless browsing)
- Scrapling MCP server for anti-bot web content extraction
- Desktop notification system with progress tracking

### Fixed
- Memory leak in ChromaDB connection pool after 72h continuous operation
- Skill deduplication logic producing false positives on similar tool chains

## [3.0.0] — 2025-11-28

### Added
- **Full MCP-native rewrite** — 16 specialized servers replacing monolithic architecture
- 9 intelligent task chains with automatic classification
- 3-tier memory: Working → Episodic → Semantic (ChromaDB)
- Semantic cache engine with 0.92 similarity threshold
- Multi-agent collaboration protocol (OMO Sisyphus)
- Pentest automation: Nmap, Nuclei, Shodan, CVE lookup
- Hermes self-learning skill extraction loop

### Breaking Changes
- Complete API surface change from v2.x — see [Migration Guide](docs/MIGRATION_v2_to_v3.md)
- `.env` format changed to support 56-key pool notation
- Removed Flask dependency — now pure MCP + FastAPI

## [2.4.0] — 2025-08-15

### Added
- OpenManus bridge compatibility layer
- 25-provider LLM routing with auto-failover
- Brain chain with task-aware model selection
- Hinglish language support in task router

### Fixed
- API key rotation not resetting cooldown timer after successful request
- WebSocket disconnection on messages >64KB

## [2.3.0] — 2025-05-22

### Added
- Semantic similarity cache (prototype, Redis-backed)
- Multi-IDE config generator (`opencode.json`, `claude_desktop_config.json`)
- WhatsApp integration via Baileys

### Changed
- Migrated from GPT-4 dependency to fully free-tier provider stack

## [2.2.0] — 2025-02-10

### Added
- Groq integration (first free-tier provider)
- Voice interface with wake word detection
- System tray application for Windows

## [2.1.0] — 2024-10-03

### Added
- Flask-based GUI dashboard
- Real-time WebSocket streaming
- Screenshot + OCR pipeline

## [2.0.0] — 2024-06-18

### Added
- Complete rewrite from v1 monolith to modular architecture
- Plugin system for extending capabilities
- Multi-model routing (GPT-4, Claude, Gemini)

## [1.0.0] — 2023-09-01

### Added
- Initial release — single-model AI assistant
- Basic command routing and file operations
- Shell execution with safety guards
