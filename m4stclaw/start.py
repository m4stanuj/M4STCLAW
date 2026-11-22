"""
start.py — Unified System Launcher & Dependency Checker
=========================================================
Performs dependency checks, resolves configuration directories, and runs
the FastAPI dashboard coordinator on localhost.
"""

import os
import sys
import logging
import re
import secrets
from threading import Thread

# Configure console logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout
)
log = logging.getLogger("m4stclaw.start")
TOKEN_ENV = "M4STCLAW_API_TOKEN"
DASHBOARD_URL = "http://127.0.0.1:8000"

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
    """Initializes local configuration without trusting the working directory."""
    from m4stclaw.core.config import CONFIG_DIR
    CONFIG_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    
    env_file = CONFIG_DIR / ".env"
    try:
        fd = os.open(env_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return
    with os.fdopen(fd, "w", encoding="utf-8") as config:
        config.write(
            "# M4STCLAW API Configuration Secrets\n"
            "M4STCLAW_API_TOKEN=\n"
            "GROQ_API_KEY=\n"
            "GEMINI_API_KEY=\n"
            "OPENROUTER_API_KEY=\n"
            "DEEPSEEK_API_KEY=\n"
            "CEREBRAS_API_KEY=\n"
            "COMPOSIO_API_KEY=\n"
        )
    log.info("Initialized empty configuration at %s", env_file)


def open_dashboard():
    from ctypes import windll

    # Launch the system browser with Windows' normal DLL search path.
    set_dll_directory = windll.kernel32.SetDllDirectoryW
    if not set_dll_directory(None):
        log.info("Open %s in your browser.", DASHBOARD_URL)
        return
    try:
        os.startfile(DASHBOARD_URL)
    except OSError:
        log.info("Open %s in your browser.", DASHBOARD_URL)
    finally:
        set_dll_directory(sys._MEIPASS)


def run_interactive_dashboard(session_token, *, open_browser=True):
    import uvicorn
    from m4stclaw.ui.app_server import app

    class DesktopServer(uvicorn.Server):
        async def startup(self, sockets=None):
            await super().startup(sockets=sockets)
            if self.started:
                print(f"Dashboard ready at {DASHBOARD_URL}", flush=True)
                if session_token:
                    print(f"Paste this session token into the dashboard: {session_token}", flush=True)
                if open_browser:
                    Thread(target=open_dashboard, daemon=True).start()

    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="warning")
    app.state.desktop_session_token = session_token
    try:
        DesktopServer(config).run()
    finally:
        del app.state.desktop_session_token

def main():
    log.info("Initializing M4STCLAW v3.6.0...")
    
    if not check_dependencies():
        sys.exit(1)
        
    setup_config_directory()

    # Load the locally-created configuration before checking access controls.
    from m4stclaw.core.config import CONFIG_DIR, load_dotenv_simple
    load_dotenv_simple(CONFIG_DIR / ".env")
    desktop = sys.platform == "win32" and getattr(sys, "frozen", False)
    interactive = desktop and sys.stdout is not None and sys.stdout.isatty()
    token = os.environ.get(TOKEN_ENV, "")
    session_token = None
    if not token and interactive:
        token = session_token = secrets.token_urlsafe(32)
    if not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", token):
        log.error("Set M4STCLAW_API_TOKEN to a high-entropy token (32–128 URL-safe characters) in %s.", CONFIG_DIR / ".env")
        sys.exit(1)

    if interactive:
        run_interactive_dashboard(session_token, open_browser="--no-browser" not in sys.argv[1:])
        return

    # Start the FastAPI Dashboard Server via Uvicorn
    import uvicorn
    
    log.info("Starting authenticated M4STCLAW App Server on http://localhost:8000")
    print("\n" + "="*80)
    print("  M4STCLAW v3.6.0 Dashboard is running locally.")
    print("  - Web Dashboard:     http://localhost:8000")
    print("="*80 + "\n")
    
    # Listen strictly on loopback address (127.0.0.1) for secure deployment, allow overrides for containerization
    host = "127.0.0.1" if desktop else os.environ.get("M4STCLAW_HOST", "127.0.0.1")
    uvicorn.run(
        "m4stclaw.ui.app_server:app",
        host=host,
        port=8000,
        log_level="warning",
        reload=False
    )

if __name__ == "__main__":
    main()
