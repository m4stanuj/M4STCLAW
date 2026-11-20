import pytest
from fastapi.testclient import TestClient

from m4stclaw.ui.app_server import app
from m4stclaw.ui import app_server
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
