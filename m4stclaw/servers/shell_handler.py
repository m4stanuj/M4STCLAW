"""
shell_handler.py — Secure Command Runner
===========================================
Safe system command execution wrapper. Restricts commands to a sandbox directory
and checks binaries against a strict allow-list.
"""

import os
import shlex
import shutil
import subprocess
import logging
from typing import Tuple

log = logging.getLogger("m4stclaw.servers.shell")

# Allowed command binaries
ALLOWED_BINARIES = {
    "git", "python", "python3", "pip", "pip3", "npm", "node", "pytest",
    "nmap", "nuclei", "shodan", "echo", "dir", "ls", "pwd"
}

# Restrict to scratch sandbox directory (configurable via env)
DEFAULT_SANDBOX = os.path.abspath(os.path.expanduser("~/.gemini/antigravity-ide/scratch"))
if not os.path.exists(DEFAULT_SANDBOX):
    # Fallback to project root or current working directory if default doesn't exist
    DEFAULT_SANDBOX = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

SANDBOX_DIR = os.path.abspath(os.environ.get("M4STCLAW_SANDBOX", DEFAULT_SANDBOX))

def is_command_safe(cmd_str: str) -> Tuple[bool, str]:
    """Validates the first word of the command against our safe allow-list."""
    parts = cmd_str.strip().split()
    if not parts:
        return False, "Empty command."
        
    binary = os.path.basename(parts[0]).lower()
    # Handle windows extensions (.exe, .bat, etc.)
    binary_base = os.path.splitext(binary)[0]
    
    if binary_base not in ALLOWED_BINARIES:
        return False, f"Command binary '{parts[0]}' is not in the allowed list of developer tools."
        
    # Check for suspicious redirection/chaining characters to prevent command injection
    suspicious = [";", "&&", "||", "|", "`", "$("]
    for char in suspicious:
        if char in cmd_str:
            # If the user is chain-running, verify all parts
            return False, f"Chained commands containing '{char}' are blocked for security."
            
    return True, ""

def execute_command(cmd_str: str, cwd: str = ".") -> str:
    """Executes a command safely inside the sandbox directory using shell=False."""
    # Resolve CWD and ensure directory boundary check
    cwd_resolved = os.path.abspath(os.path.join(SANDBOX_DIR, cwd))
    
    # Enforce strict boundary check to prevent traversal
    sandbox_norm = os.path.join(SANDBOX_DIR, "")
    cwd_norm = os.path.join(cwd_resolved, "")
    
    if not cwd_norm.startswith(sandbox_norm):
        return f"ERROR: Path Traversal Detected. Command CWD must reside within the sandbox: {SANDBOX_DIR}"
        
    # Validate command safety
    safe, reason = is_command_safe(cmd_str)
    if not safe:
        return f"SECURITY BLOCK: {reason}"
        
    try:
        # Safely split command arguments (posix=False preserves Windows backslashes)
        args = shlex.split(cmd_str, posix=False)
        if not args:
            return "ERROR: Empty command."
            
        binary = args[0]
        # Check if binary is standalone executable
        executable = shutil.which(binary)
        
        # Windows command prompt built-ins fallback (echo, dir, etc.)
        if not executable and os.name == "nt" and binary.lower() in ("dir", "echo"):
            cmd_args = ["cmd.exe", "/c"] + args
            executable = shutil.which("cmd.exe") or "cmd.exe"
        else:
            cmd_args = args
            if not executable:
                return f"ERROR: Command executable '{binary}' not found on system PATH."
                
        log.info(f"Running command (shell=False): {cmd_args} in '{cwd_resolved}'")
        
        # Run process safely
        res = subprocess.run(
            cmd_args,
            shell=False,
            cwd=cwd_resolved,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=45  # timeout to prevent infinite hangs
        )
        
        output = res.stdout if res.stdout else ""
        errors = res.stderr if res.stderr else ""
        
        if res.returncode == 0:
            return output if output else "Command executed successfully (no output)."
        else:
            return f"Command returned exit code {res.returncode}.\nSTDOUT:\n{output}\nSTDERR:\n{errors}"
            
    except subprocess.TimeoutExpired:
        return "ERROR: Command execution timed out (limit: 45 seconds)."
    except Exception as e:
        return f"ERROR executing command: {str(e)}"
