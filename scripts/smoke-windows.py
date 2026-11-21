"""Exercise the Windows binary from an isolated profile without Python on its PATH."""

import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

import httpx
import win32api
import win32con
import win32job


def smoke_test(executable: Path) -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 8000))

    system_env = {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATHEXT", "COMSPEC"}
    env = {key: os.environ[key] for key in system_env if key in os.environ}
    env["PATH"] = str(Path(env["SYSTEMROOT"]) / "System32")
    env["PYTHONUTF8"] = "1"

    with tempfile.TemporaryDirectory(prefix="m4stclaw-smoke-") as profile:
        config = Path(profile) / "config"
        env["M4STCLAW_CONFIG"] = str(config)
        initial = subprocess.run([executable], cwd=profile, env=env, capture_output=True, timeout=30)
        assert initial.returncode == 1 and b"M4STCLAW_API_TOKEN" in initial.stdout, initial.stdout + initial.stderr
        assert (config / ".env").is_file()

        token = "windows-smoke-fixture-token-0123456789"
        env["M4STCLAW_API_TOKEN"] = token
        job = win32job.CreateJobObject(None, "")
        limits = win32job.QueryInformationJobObject(job, win32job.JobObjectExtendedLimitInformation)
        limits["BasicLimitInformation"]["LimitFlags"] |= win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        win32job.SetInformationJobObject(job, win32job.JobObjectExtendedLimitInformation, limits)

        with subprocess.Popen(
            [executable], cwd=profile, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        ) as process:
            try:
                access = win32con.PROCESS_SET_QUOTA | win32con.PROCESS_TERMINATE
                handle = win32api.OpenProcess(access, False, process.pid)
                try:
                    win32job.AssignProcessToJobObject(job, handle)
                finally:
                    handle.Close()

                with httpx.Client(base_url="http://127.0.0.1:8000", trust_env=False, timeout=2) as client:
                    verify_dashboard(process, client, token)
            finally:
                job.Close()
                if process.poll() is None:
                    process.kill()
                stdout, _ = process.communicate(timeout=10)
                if sys.exc_info()[0] is not None:
                    print(stdout.decode("utf-8", errors="replace"))


def verify_dashboard(process: subprocess.Popen, client: httpx.Client, token: str) -> None:
    deadline = time.monotonic() + 30
    while True:
        if process.poll() is not None:
            raise RuntimeError(f"Startup exited with status {process.returncode}.")
        try:
            dashboard = client.get("/")
            break
        except (httpx.ConnectError, httpx.ConnectTimeout):
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.2)

    assert dashboard.status_code == 200 and "dashboard-unlock" in dashboard.text
    assert "--glass-shadow" in client.get("/style.css").text
    assert client.get("/app.js").status_code == 200
    assert client.get("/", headers={"Host": "invalid.example"}).status_code == 400
    assert client.get("/api/telemetry").status_code == 401
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/telemetry", headers=headers).json()["completed_runs"] == 0
    assert client.post("/api/keys", headers=headers, json={}).json()["updated"] == 0
    assert client.get("/mcp/sse", headers=headers).status_code == 404


if __name__ == "__main__":
    smoke_test(Path(sys.argv[1]).resolve(strict=True))
    print("Windows startup, bundled dashboard, and authorization checks passed.")
