"""
config.py — Configuration and API Key Manager
===============================================
Loads environment variables and rotates keys with thread-safe cooldowns.
"""

import os
import re
import time
import logging
import threading
from typing import Dict, List, Tuple, Optional
from pathlib import Path

log = logging.getLogger("m4stclaw.core.config")

# Find config directory (~/.config/m4stclaw or similar)
def get_config_dir() -> Path:
    env = os.environ.get("M4STCLAW_CONFIG")
    if env:
        return Path(env)
    return Path(os.path.expanduser("~/.config/m4stclaw"))

CONFIG_DIR = get_config_dir()

def load_dotenv_simple(path: Path):
    """Simple .env loader — no external dependency."""
    if not path.exists():
        return
    try:
        content = path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if val and key not in os.environ:
                os.environ[key] = val
    except Exception as e:
        log.error(f"Error reading .env: {e}")

# Load .env files from potential directories
for env_path in [
    CONFIG_DIR / ".env",
    Path(".env"),
    Path("../.env"),
]:
    if env_path.exists():
        load_dotenv_simple(env_path)
        log.info(f"Loaded config from {env_path.resolve()}")
        break

# Key Rotator State
_COOLDOWNS: Dict[str, float] = {}
_COOLDOWNS_LOCK = threading.Lock()
_ROTATION_LOCK = threading.Lock()

def _load_keys(prefix: str) -> List[str]:
    """Load API keys with the given prefix from environment."""
    keys = []
    base = os.getenv(f"{prefix}_API_KEY", "").strip()
    if base:
        keys.append(base)
    for i in range(1, 31):
        k = os.getenv(f"{prefix}_API_KEY_{i}", "").strip()
        if k:
            keys.append(k)
    return list(dict.fromkeys(keys))  # deduplicate

def _load_smart_keys() -> Dict[str, List[str]]:
    """Automatically categorizes keys prefixed with SMART_KEY_N."""
    uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
    smart_keys: Dict[str, List[str]] = {}
    
    for i in range(1, 60):
        val = os.getenv(f"SMART_KEY_{i}", "").strip()
        if not val:
            continue
        if val.startswith("gsk_"):
            smart_keys.setdefault("GROQ", []).append(val)
        elif val.startswith("csk-"):
            smart_keys.setdefault("CEREBRAS", []).append(val)
        elif val.startswith("AIza"):
            smart_keys.setdefault("GEMINI", []).append(val)
        elif val.startswith("sk-or-"):
            smart_keys.setdefault("OPENROUTER", []).append(val)
        elif val.startswith("nvapi-"):
            smart_keys.setdefault("NVIDIA", []).append(val)
        elif val.startswith("msk-"):
            smart_keys.setdefault("MISTRAL", []).append(val)
        elif val.startswith("xai-"):
            smart_keys.setdefault("GROKAI", []).append(val)
        elif val.startswith("hf_"):
            smart_keys.setdefault("HUGGINGFACE", []).append(val)
        elif val.startswith("sk-ant-"):
            smart_keys.setdefault("ANTHROPIC", []).append(val)
        elif uuid_pattern.match(val):
            smart_keys.setdefault("SAMBANOVA", []).append(val)
        elif val.startswith("sk-"):
            # DeepSeek or Together fallback logic
            smart_keys.setdefault("DEEPSEEK", []).append(val)
            smart_keys.setdefault("TOGETHER", []).append(val)
            
    return smart_keys

_smart_map = _load_smart_keys()

def get_keys_for_provider(provider_name: str) -> List[str]:
    """Retrieve explicit keys and detected smart keys for a provider."""
    prefix = provider_name.upper()
    explicit = _load_keys(prefix)
    
    # Reload smart keys dynamically to ensure new keys set via API are instantly detected
    global _smart_map
    _smart_map = _load_smart_keys()
    
    smart = _smart_map.get(prefix, [])
    merged = list(dict.fromkeys(explicit + smart))
    return merged if merged else ["PLACEHOLDER_NO_KEY"]

# Thread-safe Key Rotation with Cooldowns
_key_indices: Dict[str, int] = {}

def get_next_key(provider_name: str, keys: List[str]) -> Tuple[str, int]:
    """Returns the next available uncooled key for the provider."""
    if not keys or keys == ["PLACEHOLDER_NO_KEY"]:
        return "PLACEHOLDER_NO_KEY", 0
        
    with _ROTATION_LOCK:
        now = time.time()
        start_idx = _key_indices.get(provider_name, 0)
        n_keys = len(keys)
        
        for offset in range(n_keys):
            idx = (start_idx + offset) % n_keys
            key_id = f"{provider_name}:{idx}"
            
            with _COOLDOWNS_LOCK:
                cooldown_time = _COOLDOWNS.get(key_id, 0.0)
                is_cooled = cooldown_time > now
                
            if not is_cooled:
                _key_indices[provider_name] = (idx + 1) % n_keys
                return keys[idx], idx
                
        # If all keys cooled, return the current index key anyway
        fallback_idx = start_idx % n_keys
        _key_indices[provider_name] = (fallback_idx + 1) % n_keys
        return keys[fallback_idx], fallback_idx

def set_cooldown(provider_name: str, key_idx: int, duration_sec: float):
    """Sets a temporary cooldown on a specific key."""
    key_id = f"{provider_name}:{key_idx}"
    with _COOLDOWNS_LOCK:
        _COOLDOWNS[key_id] = time.time() + duration_sec
        log.warning(f"Cooldown set on key {key_id} for {duration_sec}s")

def get_cooldowns_status() -> Dict[str, float]:
    """Retrieve active cooldown times left."""
    now = time.time()
    with _COOLDOWNS_LOCK:
        return {k: max(0.0, v - now) for k, v in _COOLDOWNS.items() if v > now}
