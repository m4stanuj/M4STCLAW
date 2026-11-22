"""Exercise first-run onboarding in an isolated Windows pseudo-console."""

from contextlib import contextmanager, ExitStack
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import re
import socket
import sys
import tempfile
from threading import Thread
import time

import httpx
import win32api
import win32con
import win32job
from winpty import Backend, PTY, WinptyError


DASHBOARD = "http://127.0.0.1:8000"
TOKEN_PROMPT = re.compile(r"Paste this session token into the dashboard: ([A-Za-z0-9_-]{32,128})(?=\s)")
ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
OFFLINE_PROMPT = "Reply with a short greeting."
OFFLINE_REPLY = "Hello from the local fixture."


class OfflineFixture(BaseHTTPRequestHandler):
    def do_POST(self):
        self.connection.settimeout(5)
        size = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(size))
        if self.path != "/v1/chat/completions" or body.get("stream") is not True:
            self.send_error(400, "Unexpected local completion request")
            return
        if body["messages"][-1] != {"role": "user", "content": OFFLINE_PROMPT}:
            self.send_error(400, "Unexpected local prompt")
            return

        content = json.dumps({"choices": [{"delta": {"content": OFFLINE_REPLY}}]})
        payload = f"data: {content}\n\ndata: [DONE]\n\n".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        pass


def verify_offline_prompt(client: httpx.Client, authorization: dict) -> None:
    with ExitStack() as stack:
        # A real Ollama instance may already own this port. Never contact or stop it.
        if socket.has_ipv6:
            ipv6_guard = stack.enter_context(socket.socket(socket.AF_INET6))
            ipv6_guard.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            try:
                ipv6_guard.bind(("::1", 11434))
            except OSError as error:
                if error.winerror != 10049:  # IPv6 loopback unavailable.
                    raise
        server = stack.enter_context(HTTPServer(("127.0.0.1", 11434), OfflineFixture, bind_and_activate=False))
        server.allow_reuse_address = False
        server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        server.server_bind()
        server.server_activate()
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            response = client.post(
                "/api/execute/stream", headers=authorization,
                json={"prompt": OFFLINE_PROMPT, "task": "offline"},
            )
            assert response.raise_for_status().text == OFFLINE_REPLY, "The offline stream did not return the fixture reply."
            telemetry = client.get("/api/telemetry", headers=authorization)
            assert telemetry.raise_for_status().json()["completed_runs"] == 1
        finally:
            server.shutdown()
            worker.join()


@contextmanager
def interactive_launch(executable: Path, profile: Path):
    # The child inherits neither the user's provider credentials nor their config path.
    env = {name: os.environ[name] for name in ("SYSTEMROOT", "WINDIR", "COMSPEC") if name in os.environ}
    env.update(
        PATH=str(Path(env["SYSTEMROOT"]) / "System32"),
        TEMP=str(profile),
        TMP=str(profile),
        M4STCLAW_CONFIG=str(profile / "config"),
        NO_PROXY="localhost,127.0.0.1",
        PYTHONUTF8="1",
    )
    env_block = "\0".join(f"{name}={value}" for name, value in sorted(env.items())) + "\0\0"
    console = PTY(132, 35, backend=Backend.ConPTY)
    with ExitStack() as handles:
        job = win32job.CreateJobObject(None, "")
        handles.callback(job.Close)
        limits = win32job.QueryInformationJobObject(job, win32job.JobObjectExtendedLimitInformation)
        limits["BasicLimitInformation"]["LimitFlags"] |= win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        win32job.SetInformationJobObject(job, win32job.JobObjectExtendedLimitInformation, limits)
        if not console.spawn(str(executable), cmdline=" --no-browser", cwd=str(profile), env=env_block):
            raise RuntimeError("Could not launch the packaged EXE in ConPTY.")
        access = win32con.PROCESS_SET_QUOTA | win32con.PROCESS_TERMINATE
        handle = win32api.OpenProcess(access, False, console.pid)
        handles.callback(handle.Close)
        try:
            win32job.AssignProcessToJobObject(job, handle)
        except Exception:
            win32api.TerminateProcess(handle, 1)
            raise
        try:
            yield console
        finally:
            # Let the PyInstaller bootloader clean up its extracted runtime.
            if console.isalive():
                try:
                    console.write("\x03")
                except WinptyError:
                    pass
            if not wait_for_exit(job, timeout=3):
                win32job.TerminateJobObject(job, 1)
                if not wait_for_exit(job, timeout=10):
                    raise RuntimeError("The test EXE did not stop within 10 seconds.")


def wait_for_exit(job, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        stats = win32job.QueryInformationJobObject(job, win32job.JobObjectBasicAccountingInformation)
        if stats["ActiveProcesses"] == 0:
            return True
        time.sleep(0.1)
    return False


def read_session_token(console: PTY) -> str:
    deadline = time.monotonic() + 45
    output = ""
    while time.monotonic() < deadline:
        if not console.isalive():
            raise RuntimeError(f"The test EXE exited before readiness with status {console.get_exitstatus()}.")
        output = (output + console.read(blocking=False))[-16384:]
        match = TOKEN_PROMPT.search(ANSI_ESCAPE.sub("", output))
        if match:
            return match[1]
        time.sleep(0.1)
    raise RuntimeError("The test EXE did not announce a session token within 45 seconds.")


def smoke_test(executable: Path) -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 8000))
    with tempfile.TemporaryDirectory(prefix="m4st-interactive-") as directory:
        profile = Path(directory)
        env_file = profile / "config" / ".env"
        fake_key = "fixture-only-groq-key"

        with interactive_launch(executable, profile) as console:
            token = read_session_token(console)
            with httpx.Client(base_url=DASHBOARD, trust_env=False, timeout=5) as client:
                assert "dashboard-unlock" in client.get("/").raise_for_status().text
                assert client.get("/api/auth/check").status_code == 401
                authorization = {"Authorization": f"Bearer {token}"}
                assert client.get("/api/auth/check", headers=authorization).json() == {"status": "authenticated"}
                config = env_file.read_text(encoding="utf-8")
                assert "M4STCLAW_API_TOKEN=" in config.splitlines()
                assert token not in config
                save = client.post("/api/keys", headers=authorization, json={"groq": fake_key})
                assert save.raise_for_status().json()["updated"] == 1
                no_op = client.post("/api/keys", headers=authorization, json={"groq": ""})
                assert no_op.raise_for_status().json()["updated"] == 0
                assert f"GROQ_API_KEY={fake_key}" in env_file.read_text(encoding="utf-8").splitlines()
                verify_offline_prompt(client, authorization)

        with interactive_launch(executable, profile) as console:
            new_token = read_session_token(console)
            assert new_token != token
            with httpx.Client(base_url=DASHBOARD, trust_env=False, timeout=5) as client:
                assert client.get("/api/auth/check", headers=authorization).status_code == 401
                telemetry = client.get("/api/telemetry", headers={"Authorization": f"Bearer {new_token}"})
                assert telemetry.raise_for_status().json()["keys_configured"] == 1
                assert fake_key not in telemetry.text


if __name__ == "__main__":
    smoke_test(Path(sys.argv[1]).resolve(strict=True))
    print("Windows interactive startup, session authorization, offline completion, and provider settings across restart passed.")
