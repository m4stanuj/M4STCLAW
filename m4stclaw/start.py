"""
start.py — Unified System Launcher & Dependency Checker
=========================================================
Performs dependency checks, resolves configuration directories, and runs
the FastAPI dashboard coordinator on localhost.
"""

import os
import sys
import logging
import shutil
from pathlib import Path

# Configure console logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout
)
log = logging.getLogger("m4stclaw.start")

# Verify local dependencies
REQUIRED_PACKAGES = [
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("httpx", "httpx"),
    ("pydantic", "pydantic"),
    ("mcp", "mcp"),
    ("PIL", "pillow"),
    ("requests", "requests")
]

def check_dependencies() -> bool:
    """Verifies that all core packages are installed, showing warnings for missing ones."""
    missing = []
    for module_name, package_name in REQUIRED_PACKAGES:
        try:
            __import__(module_name)
        except ImportError:
            missing.append(package_name)
            
    if missing:
        log.error("Missing required dependencies!")
        print("\nPlease run the following command to install the missing libraries:")
        print(f"  pip install {' '.join(missing)}")
        print("Or use the configured requirements.txt:")
        print("  pip install -r requirements.txt\n")
        return False
        
    log.info("Dependency checks passed.")
    return True

def setup_config_directory():
    """Initializes local configuration folders and copies template files if needed."""
    from m4stclaw.core.config import CONFIG_DIR
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    env_file = CONFIG_DIR / ".env"
    if not env_file.exists():
        template_file = Path(".env.template")
        if template_file.exists():
            shutil.copy(template_file, env_file)
            log.info(f"Created config .env template at: {env_file}")
        else:
            # Create a blank env file
            env_file.write_text(
                "# M4STCLAW API Configuration Secrets\n"
                "GROQ_API_KEY=\n"
                "GEMINI_API_KEY=\n"
                "OPENROUTER_API_KEY=\n"
                "DEEPSEEK_API_KEY=\n"
                "CEREBRAS_API_KEY=\n"
                "COMPOSIO_API_KEY=\n",
                encoding="utf-8"
            )
            log.info(f"Initialized empty .env configurations at: {env_file}")

def main():
    log.info("Initializing M4STCLAW v3.4.0...")
    
    if not check_dependencies():
        sys.exit(1)
        
    setup_config_directory()
    
    # Start the FastAPI Dashboard Server via Uvicorn
    import uvicorn
    
    log.info("Starting M4STCLAW App Server on http://localhost:8000")
    print("\n" + "="*80)
    print("  M4STCLAW v3.4.0 Dashboard is running locally.")
    print("  - Web Dashboard:     http://localhost:8000")
    print("  - Unified MCP HTTP:  http://localhost:8000/mcp")
    print("="*80 + "\n")
    
    # Listen strictly on loopback address (127.0.0.1) for secure deployment, allow overrides for containerization
    host = os.environ.get("M4STCLAW_HOST", "127.0.0.1")
    uvicorn.run(
        "m4stclaw.ui.app_server:app",
        host=host,
        port=8000,
        log_level="warning",
        reload=False
    )

if __name__ == "__main__":
    main()
