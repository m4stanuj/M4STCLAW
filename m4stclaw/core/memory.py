"""
memory.py — 3-Tier Memory Engine
================================
Implements:
  - T1: Working Memory (Session-specific JSON state in RAM)
  - T2: Episodic Memory (Cross-session task history logs)
  - T3: Semantic Memory (Permanent vector embeddings via ChromaDB or fallback)
"""

import os
import re
import math
import json
import time
import logging
from typing import Dict, List, Any, Optional
from m4stclaw.core.config import CONFIG_DIR

log = logging.getLogger("m4stclaw.core.memory")

EPISODIC_FILE = CONFIG_DIR / "m4stclaw_episodic.json"

# In-memory Working Memory (T1)
_working_state: Dict[str, Any] = {}

# Episodic Memory (T2)
_episodic_logs: List[Dict[str, Any]] = []

# T3 ChromaDB initialization with fallback
_chroma_client = None
_chroma_collection = None

try:
    import chromadb
    from chromadb.config import Settings
    
    db_path = str(CONFIG_DIR / "chromadb")
    _chroma_client = chromadb.PersistentClient(path=db_path)
    # Get or create collection for permanent semantic memories
    _chroma_collection = _chroma_client.get_or_create_collection(
        name="m4stclaw_semantic_memory",
        metadata={"hnsw:space": "cosine"}
    )
    log.info("ChromaDB Semantic Memory collection initialized successfully.")
except Exception as e:
    log.warning(f"ChromaDB not available or failed to load ({e}). Falling back to simple JSON storage.")

# ═══════════════════════════════════════════════════════════════
# T1: WORKING MEMORY (In-Session)
# ═══════════════════════════════════════════════════════════════

def get_working_value(key: str, default: Any = None) -> Any:
    return _working_state.get(key, default)

def set_working_value(key: str, value: Any):
    _working_state[key] = value

def clear_working_memory():
    _working_state.clear()
    log.info("Working memory cleared.")

# ═══════════════════════════════════════════════════════════════
# T2: EPISODIC MEMORY (Cross-Session Logs)
# ═══════════════════════════════════════════════════════════════

def load_episodic_memory():
    global _episodic_logs
    if not EPISODIC_FILE.exists():
        _episodic_logs = []
        return
    try:
        _episodic_logs = json.loads(EPISODIC_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        log.error(f"Error loading episodic memory: {e}")
        _episodic_logs = []

def save_episodic_memory():
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        EPISODIC_FILE.write_text(json.dumps(_episodic_logs, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        log.error(f"Error saving episodic memory: {e}")

def add_episodic_log(task_type: str, query: str, response: str, success: bool = True):
    load_episodic_memory()
    log_entry = {
        "timestamp": time.time(),
        "task_type": task_type,
        "query": query[:500],  # cap queries to save space
        "response": response[:1000],  # cap responses
        "success": success
    }
    _episodic_logs.append(log_entry)
    
    # Keep last 1000 logs
    if len(_episodic_logs) > 1000:
        _episodic_logs.pop(0)
        
    save_episodic_memory()

def search_episodic_logs(task_type: Optional[str] = None, keyword: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
    load_episodic_memory()
    filtered = _episodic_logs
    
    if task_type:
        filtered = [entry for entry in filtered if entry["task_type"] == task_type]
        
    if keyword:
        kw = keyword.lower()
        filtered = [entry for entry in filtered if kw in entry["query"].lower() or kw in entry["response"].lower()]
        
    return list(reversed(filtered))[:limit]

# ═══════════════════════════════════════════════════════════════
# T3: SEMANTIC MEMORY (Permanent Embeddings)
# ═══════════════════════════════════════════════════════════════
# For the fallback, we store semantic memories in a simple local JSON file.
_FALLBACK_FILE = CONFIG_DIR / "m4stclaw_semantic_fallback.json"
_fallback_memories: List[Dict[str, Any]] = []

def load_fallback_memories():
    global _fallback_memories
    if not _FALLBACK_FILE.exists():
        return
    try:
        _fallback_memories = json.loads(_FALLBACK_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        log.error(f"Error loading fallback semantic memory: {e}")

def save_fallback_memories():
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        _FALLBACK_FILE.write_text(json.dumps(_fallback_memories, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        log.error(f"Error saving fallback semantic memory: {e}")

load_fallback_memories()

def add_semantic_memory(text: str, metadata: Optional[Dict[str, Any]] = None):
    """Saves a permanent memory item into ChromaDB or fallback storage."""
    metadata = metadata or {}
    mem_id = f"mem_{int(time.time() * 1000)}"
    
    if _chroma_collection is not None:
        try:
            _chroma_collection.add(
                documents=[text],
                metadatas=[metadata],
                ids=[mem_id]
            )
            log.info(f"Saved semantic memory '{mem_id}' to ChromaDB.")
            return
        except Exception as e:
            log.error(f"ChromaDB insert failed: {e}. Storing in JSON fallback.")
            
    # Fallback storage
    _fallback_memories.append({
        "id": mem_id,
        "text": text,
        "metadata": metadata,
        "timestamp": time.time()
    })
    save_fallback_memories()

def query_semantic_memory(query_text: str, limit: int = 3) -> List[Dict[str, Any]]:
    """Queries semantic memory collections for relevant past inputs."""
    if _chroma_collection is not None:
        try:
            results = _chroma_collection.query(
                query_texts=[query_text],
                n_results=limit
            )
            ret = []
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            ids = results.get("ids", [[]])[0]
            
            for i in range(len(documents)):
                ret.append({
                    "id": ids[i],
                    "text": documents[i],
                    "metadata": metadatas[i]
                })
            return ret
        except Exception as e:
            log.error(f"ChromaDB query failed: {e}. Searching JSON fallback.")
            
    # Fallback simple search (Upgraded to TF-IDF + Cosine Similarity)
    if not _fallback_memories:
        return []
        
    ret = []
    
    def tokenize(text: str) -> List[str]:
        return re.findall(r'\w+', text.lower())
        
    documents = [mem["text"] for mem in _fallback_memories]
    doc_tokens_list = [tokenize(doc) for doc in documents]
    query_tokens = tokenize(query_text)
    
    if not query_tokens:
        return []
        
    # Build vocabulary
    vocab = set(query_tokens)
    for tokens in doc_tokens_list:
        vocab.update(tokens)
    vocab = list(vocab)
    vocab_idx = {word: i for i, word in enumerate(vocab)}
    
    # Calculate Document Frequency (DF)
    df = {word: 0 for word in vocab}
    for tokens in doc_tokens_list:
        for word in set(tokens):
            if word in df:
                df[word] += 1
    for word in set(query_tokens):
        df[word] += 1
        
    # Calculate Inverse Document Frequency (IDF)
    n_docs = len(documents) + 1
    idf = {}
    for word in vocab:
        idf[word] = math.log(n_docs / df[word]) + 1.0
        
    def get_tfidf_vector(tokens: List[str]) -> List[float]:
        tf = {}
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1
        vec = [0.0] * len(vocab)
        for token, count in tf.items():
            if token in vocab_idx:
                vec[vocab_idx[token]] = count * idf[token]
        return vec
        
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        dot_prod = sum(a * b for a, b in zip(v1, v2))
        norm_a = math.sqrt(sum(a * a for a in v1))
        norm_b = math.sqrt(sum(b * b for b in v2))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot_prod / (norm_a * norm_b)
        
    query_vec = get_tfidf_vector(query_tokens)
    scored = []
    for idx, mem in enumerate(_fallback_memories):
        doc_vec = get_tfidf_vector(doc_tokens_list[idx])
        score = cosine_similarity(query_vec, doc_vec)
        scored.append((score, mem))
        
    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)
    
    for score, mem in scored[:limit]:
        if score > 0.05:  # filter threshold
            ret.append({
                "id": mem["id"],
                "text": mem["text"],
                "metadata": mem["metadata"]
            })
            
    return ret

# Self-initialize T2
load_episodic_memory()
