"""
cache.py — Semantic Fuzzy Cache
================================
Caches prompt responses locally and matches similar queries using stop-word Jaccard similarity.
Saves cache state asynchronously to prevent I/O blocking.
"""

import os
import re
import json
import time
import hashlib
import logging
import threading
from typing import Optional, Dict, Any, Set
from m4stclaw.core.config import CONFIG_DIR

log = logging.getLogger("m4stclaw.core.cache")

CACHE_FILE = CONFIG_DIR / "m4stclaw_cache.json"
CACHE_LOCK = threading.Lock()

_cache: Dict[str, Dict[str, Any]] = {}
_stats = {"hits": 0, "misses": 0, "saves": 0}

MAX_ENTRIES = 500
FUZZY_THRESHOLD = 0.82
MIN_CACHE_LEN = 15

# Regular expressions for skip patterns (dynamic or time-sensitive prompts)
SKIP_PATTERNS = [
    r'current time', r'right now', r'screenshot', r'click', r'mouse', r'keyboard',
    r'live', r'latest', r'date today', r'today', r'now', r'generate dynamic', r'status'
]

# Normalizes query string by stripping punctuation and whitespaces
def normalize_text(text: str) -> str:
    cleaned = re.sub(r'[^\w\s]', ' ', text.lower().strip())
    return re.sub(r'\s+', ' ', cleaned)

def get_query_hash(text: str) -> str:
    return hashlib.md5(normalize_text(text).encode("utf-8")).hexdigest()

def get_word_similarity(a: str, b: str) -> float:
    """Calculates Jaccard similarity of non-stop-word sets."""
    stop_words = {
        'hai', 'karo', 'mein', 'ka', 'ki', 'ke', 'se', 'ko', 'aur', 'ya', 'toh', 'na',
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'have', 'has', 'had',
        'what', 'show', 'write', 'create', 'make', 'generate', 'run', 'execute'
    }
    
    words_a = set(normalize_text(a).split()) - stop_words
    words_b = set(normalize_text(b).split()) - stop_words
    
    if not words_a or not words_b:
        return 0.0
        
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)

def should_skip_cache(query: str) -> bool:
    """Check if query matches dynamic patterns that shouldn't be cached."""
    q = query.lower()
    return any(re.search(pat, q) for pat in SKIP_PATTERNS)

def load_cache():
    """Loads cache file from disk."""
    global _cache
    if not CACHE_FILE.exists():
        return
    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        now = time.time()
        with CACHE_LOCK:
            # Only keep entries that haven't expired
            _cache = {k: v for k, v in data.items() if v.get("expires", 0) > now}
        log.info(f"Loaded {len(_cache)} entries from semantic cache.")
    except Exception as e:
        log.error(f"Error loading cache: {e}")
        _cache = {}

def save_cache_async():
    """Trigger background save to avoid blocking execution threads."""
    def run_save():
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with CACHE_LOCK:
                data_str = json.dumps(_cache, ensure_ascii=False, indent=2)
            CACHE_FILE.write_text(data_str, encoding="utf-8")
        except Exception as e:
            log.error(f"Error writing cache to disk: {e}")
            
    threading.Thread(target=run_save, daemon=True).start()

def evict_old_entries():
    """Removes expired or least-recently-used entries if cache is full."""
    global _cache
    now = time.time()
    
    # Evict expired
    expired = [k for k, v in _cache.items() if v.get("expires", 0) < now]
    for k in expired:
        del _cache[k]
        
    # Evict LRU if still over limit
    if len(_cache) > MAX_ENTRIES:
        sorted_keys = sorted(_cache.items(), key=lambda item: item[1].get("last_hit", 0))
        to_evict = len(_cache) - MAX_ENTRIES
        for k, _ in sorted_keys[:to_evict]:
            del _cache[k]

def get_cached_response(query: str) -> Optional[str]:
    """Check cache for exact or semantically similar hits."""
    if should_skip_cache(query):
        return None
        
    now = time.time()
    query_hash = get_query_hash(query)
    
    with CACHE_LOCK:
        # 1. Try exact match
        if query_hash in _cache:
            entry = _cache[query_hash]
            if entry.get("expires", 0) > now:
                entry["last_hit"] = now
                _stats["hits"] += 1
                return entry["response"]
                
        # 2. Try fuzzy Jaccard match
        best_sim = 0.0
        best_key = None
        
        for k, entry in _cache.items():
            if entry.get("expires", 0) <= now:
                continue
            sim = get_word_similarity(query, entry.get("query", ""))
            if sim > best_sim:
                best_sim = sim
                best_key = k
                
        if best_sim >= FUZZY_THRESHOLD and best_key:
            entry = _cache[best_key]
            entry["last_hit"] = now
            _stats["hits"] += 1
            log.info(f"Fuzzy cache match: {round(best_sim * 100, 1)}% similarity found.")
            return entry["response"]
            
    _stats["misses"] += 1
    return None

def set_cached_response(query: str, response: str, ttl_seconds: int = 3600):
    """Save response into the semantic cache."""
    if should_skip_cache(query) or len(response) < MIN_CACHE_LEN:
        return
        
    query_hash = get_query_hash(query)
    now = time.time()
    
    with CACHE_LOCK:
        evict_old_entries()
        _cache[query_hash] = {
            "query": query[:200],  # truncate saved query log
            "response": response,
            "cached_at": now,
            "last_hit": now,
            "expires": now + ttl_seconds
        }
        _stats["saves"] += 1
        
    save_cache_async()

def get_cache_stats() -> Dict[str, Any]:
    """Returns cache operational statistics."""
    total = _stats["hits"] + _stats["misses"]
    hit_rate = (_stats["hits"] / total * 100) if total > 0 else 0.0
    return {
        "size": len(_cache),
        "hits": _stats["hits"],
        "misses": _stats["misses"],
        "hit_rate_pct": round(hit_rate, 1),
        "saves": _stats["saves"]
    }

# Self-initialize
load_cache()
