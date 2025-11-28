# Contributing to M4STCLAW

Thank you for your interest in contributing to M4STCLAW! This document provides guidelines and information about contributing to this project.

## 🏗️ Architecture Overview

Before contributing, please familiarize yourself with the project's architecture:

```
M4STCLAW/
├── mcp_servers/          # 16 MCP server implementations
│   ├── task_router.py    # ⭐ Intelligent task classification & routing
│   ├── llm_fallback.py   # 56-key provider pool with auto-failover
│   ├── memory_mcp.py     # 3-tier memory (Working → Episodic → Semantic)
│   ├── pentest_mcp.py    # Nmap, Nuclei, Shodan integration
│   └── ...
├── bridge_core/          # Core orchestration engine
├── skills/               # Hot-reloadable skill definitions
├── config/               # Environment and provider configuration
├── tests/                # Test suites
└── docs/                 # Documentation
```

## 🚀 Getting Started

1. **Fork & Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/M4STCLAW.git
   cd M4STCLAW
   ```

2. **Set up environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # or .\venv\Scripts\activate on Windows
   pip install -r requirements.txt
   cp .env.template .env
   ```

3. **Run tests**
   ```bash
   python -m pytest tests/ -v
   ```

## 📋 Contribution Guidelines

### Code Style
- Follow PEP 8 for Python code
- Use type hints for all function signatures
- Maximum line length: 100 characters
- Use descriptive variable names

### Commit Messages
Follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` — New feature
- `fix:` — Bug fix
- `refactor:` — Code refactoring
- `docs:` — Documentation only
- `test:` — Adding/updating tests
- `perf:` — Performance improvement

### Pull Requests
1. Create a feature branch from `main`
2. Write tests for new functionality
3. Ensure all existing tests pass
4. Update documentation as needed
5. Submit PR with clear description

## 🔒 Security

If you discover a security vulnerability, please **do not** open a public issue. Instead, email security concerns to m4stanuj@users.noreply.github.com.

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.
