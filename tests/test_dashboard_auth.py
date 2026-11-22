import asyncio
import re
from types import SimpleNamespace

import pytest
import uvicorn
from fastapi.testclient import TestClient

from m4stclaw.ui.app_server import app
from m4stclaw.ui import app_server
from m4stclaw.core import config
from m4stclaw import start
from m4stclaw.start import setup_config_directory


@pytest.fixture
def client(monkeypatch):
    token = "test-only-dashboard-token-0123456789"
    monkeypatch.setenv("M4STCLAW_API_TOKEN", token)
    with TestClient(app, base_url="http://localhost") as client:
        yield client, {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("path", ["/api/execute", "/api/keys", "/api/abort", "/api/mesh/execute", "/api/execute/stream"])
def test_unauthenticated_posts_stop_before_body_validation(client, path):
    http, _ = client
    assert http.post(path).status_code == 401


def test_valid_token_unlocks_dashboard(client):
    http, headers = client
    assert http.get("/").status_code == 200
    assert http.get("/api/auth/check", headers=headers).json() == {"status": "authenticated"}
    assert http.get("/api/auth/check", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_missing_token_fails_closed(client, monkeypatch):
    http, _ = client
    monkeypatch.delenv("M4STCLAW_API_TOKEN")
    assert http.get("/api/telemetry").status_code == 503


def test_dashboard_rejects_unexpected_host_and_has_no_mcp_mount(client):
    http, headers = client
    assert http.get("/api/auth/check", headers={**headers, "Host": "untrusted.example"}).status_code == 400
    assert http.get("/mcp/sse", headers=headers).status_code == 404


def test_setup_ignores_working_directory_template(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env.template").write_text("M4STCLAW_API_TOKEN=project-value\n")
    config_dir = tmp_path / "config"
    monkeypatch.setattr("m4stclaw.core.config.CONFIG_DIR", config_dir)
    setup_config_directory()
    config = (config_dir / ".env").read_text(encoding="utf-8")
    assert "M4STCLAW_API_TOKEN=\n" in config
    assert "project-value" not in config


def test_frozen_first_run_generates_session_token_without_saving_it(tmp_path, monkeypatch):
    monkeypatch.delenv(start.TOKEN_ENV, raising=False)
    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(start, "check_dependencies", lambda: True)
    monkeypatch.setattr(start, "sys", SimpleNamespace(
        platform="win32", frozen=True, stdout=SimpleNamespace(isatty=lambda: True), argv=["M4STCLAW.exe"]
    ))
    issued = []
    monkeypatch.setattr(start, "run_interactive_dashboard", lambda token, *, open_browser: issued.append((token, open_browser)))

    start.main()

    assert len(issued) == 1 and re.fullmatch(r"[A-Za-z0-9_-]{43}", issued[0][0])
    assert issued[0][1] is True
    assert (tmp_path / ".env").read_text(encoding="utf-8").splitlines()[1] == f"{start.TOKEN_ENV}="

    monkeypatch.setenv(start.TOKEN_ENV, "configured-dashboard-token-0123456789")
    start.sys.argv.append("--no-browser")
    start.main()
    assert issued[-1] == (None, False)


@pytest.mark.parametrize(("started", "open_browser"), [(False, True), (True, False), (True, True)])
def test_desktop_opens_browser_only_after_startup(started, open_browser, client, monkeypatch, capsys):
    http, _ = client
    monkeypatch.delenv(start.TOKEN_ENV)
    monkeypatch.setenv("M4STCLAW_HOST", "0.0.0.0")
    token = "desktop-only-dashboard-token-0123456789"
    launches = []

    async def startup(server, sockets=None):
        assert server.config.host == "127.0.0.1"
        server.started = started

    def run(server):
        assert http.get("/api/auth/check").status_code == 401
        headers = {"Authorization": f"Bearer {token}"}
        assert http.get("/api/auth/check", headers=headers).status_code == 200
        asyncio.run(server.startup())

    monkeypatch.setattr(uvicorn.Server, "startup", startup)
    monkeypatch.setattr(uvicorn.Server, "run", run)
    monkeypatch.setattr(start, "Thread", lambda target, daemon: SimpleNamespace(start=lambda: launches.append(target)))
    start.run_interactive_dashboard(token, open_browser=open_browser)

    assert launches == ([start.open_dashboard] if started and open_browser else [])
    assert (token in capsys.readouterr().out) == started
    assert http.get("/api/auth/check").status_code == 503


def test_dashboard_uses_observed_runs_and_provider_configuration(client, monkeypatch):
    http, headers = client
    monkeypatch.setattr(app.state, "execution_telemetry", app_server.ExecutionTelemetry())
    monkeypatch.setattr(app_server.memory, "query_semantic_memory", lambda *args, **kwargs: [])
    monkeypatch.setattr(app_server.memory, "add_episodic_log", lambda *args: None)
    monkeypatch.setattr(app_server.cache, "get_cache_stats", lambda: {
        "hits": 0, "misses": 0, "hit_rate_pct": 0.0, "size": 0,
    })
    monkeypatch.setattr(app_server.fallback, "get_keys_for_provider", lambda name: (
        ["fixture-secret"] if name == "groq" else ["PLACEHOLDER_NO_KEY"]
    ))
    monkeypatch.setattr(app_server, "get_cooldowns_status", lambda: {"groq:0": 12.0})

    cold = http.get("/api/telemetry", headers=headers)
    assert cold.json()["last_run_duration_ms"] is None
    assert cold.json()["cache_hit_rate_pct"] is None
    assert cold.json()["completed_runs"] == 0
    assert "fixture-secret" not in cold.text
    providers = {provider["name"]: provider for provider in cold.json()["providers"]}
    assert providers["groq"]["configured_keys"] == providers["groq"]["cooling_keys"] == 1
    assert providers["ollama"]["local"]

    async def completion(*args, **kwargs):
        return "Fixture reply"

    async def failed_stream(*args, **kwargs):
        yield "ERROR: Fixture provider unavailable"

    monkeypatch.setattr(app_server.fallback, "chat_complete_async", completion)
    monkeypatch.setattr(app_server.fallback, "chat_complete_stream", failed_stream)
    request = {"prompt": "test", "task": "speed"}
    assert http.post("/api/execute", headers=headers, json=request).status_code == 200
    assert http.post("/api/execute/stream", headers=headers, json=request).text.startswith("ERROR:")

    stats = http.get("/api/telemetry", headers=headers).json()
    assert stats["completed_runs"] == 1
    assert stats["failed_runs"] == 1
    assert stats["last_run_duration_ms"] >= 0


def test_save_keys_preserves_blanks_and_changes_only_file_managed_values(client, tmp_path, monkeypatch):
    http, headers = client
    monkeypatch.setattr(app_server, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config, "_FILE_LOADED_VALUES", {})
    for name in ("GROQ_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.setenv(name, "fixture")
        monkeypatch.delenv(name)
    env_file = tmp_path / ".env"
    env_file.write_text("GROQ_API_KEY=old-test-groq\nGEMINI_API_KEY=keep-test-gemini\n# keep\n", encoding="utf-8")
    config.load_dotenv_simple(env_file)

    response = http.post("/api/keys", headers=headers, json={"groq": "new-test-groq", "gemini": ""})
    assert response.json() == {"status": "success", "updated": 1}
    assert config.get_keys_for_provider("groq")[0] == "new-test-groq"
    assert env_file.read_text(encoding="utf-8") == "GROQ_API_KEY=new-test-groq\nGEMINI_API_KEY=keep-test-gemini\n# keep\n"
    original = env_file.read_bytes()
    assert http.post("/api/keys", headers=headers, json={}).json()["updated"] == 0
    assert env_file.read_bytes() == original


def test_rejected_key_updates_leave_config_unchanged(client, tmp_path, monkeypatch):
    http, headers = client
    monkeypatch.setattr(app_server, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config, "_FILE_LOADED_VALUES", {})
    monkeypatch.setenv("GROQ_API_KEY", "managed-test-key")
    env_file = tmp_path / ".env"
    env_file.write_text("# original\n", encoding="utf-8")
    bad = http.post("/api/keys", headers=headers, json={"gemini": "incorrect test token"})
    managed = http.post("/api/keys", headers=headers, json={"groq": "new-test-value"})
    assert bad.status_code == 422
    assert managed.status_code == 409
    assert "incorrect test token" not in bad.text
    assert "managed-test-key" not in managed.text
    assert env_file.read_text(encoding="utf-8") == "# original\n"


def test_failed_atomic_save_never_changes_current_keys(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("GROQ_API_KEY=existing-test-key\n", encoding="utf-8")
    monkeypatch.setenv("GROQ_API_KEY", "fixture")
    monkeypatch.delenv("GROQ_API_KEY")
    monkeypatch.setattr(config, "_FILE_LOADED_VALUES", {})
    config.load_dotenv_simple(env_file)

    def fail_replace(*args):
        raise OSError("Fixture failed replace")

    monkeypatch.setattr(config.os, "replace", fail_replace)
    with pytest.raises(OSError):
        config.update_provider_keys(env_file, {"GROQ_API_KEY": "unused-test-key"})
    assert config.get_keys_for_provider("groq")[0] == "existing-test-key"
    assert env_file.read_text(encoding="utf-8") == "GROQ_API_KEY=existing-test-key\n"
    assert list(tmp_path.iterdir()) == [env_file]
