"""
fallback.py — Multi-Provider LLM Fallback Loop
===============================================
Executes completion requests across chains of LLM providers with automatic key rotation
and fallback upon rate-limits (HTTP 429) or failures.
"""

import time
import logging
import httpx
from typing import Dict, List, Optional, Any, Tuple
from m4stclaw.core.config import get_keys_for_provider, get_next_key, set_cooldown

log = logging.getLogger("m4stclaw.core.fallback")

# Provider definition templates
# Format: (name, base_url, model, type)
_GROQ = ("groq", "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile", "openai")
_CEREBRAS = ("cerebras", "https://api.cerebras.ai/v1", "llama-3.3-70b", "openai")
_GEMINI = ("gemini", "https://generativelanguage.googleapis.com/v1beta", "gemini-2.5-flash", "gemini")
_OPENROUTER = ("openrouter", "https://openrouter.ai/api/v1", "meta-llama/llama-3.3-70b-instruct:free", "openai")
_SAMBANOVA = ("sambanova", "https://api.sambanova.ai/v1", "Meta-Llama-3.1-405B-Instruct", "openai")
_DEEPSEEK = ("deepseek", "https://api.deepseek.com/v1", "deepseek-chat", "openai")
_DEEPSEEK_R1 = ("deepseek", "https://api.deepseek.com/v1", "deepseek-reasoner", "openai")
_TOGETHER = ("together", "https://api.together.xyz/v1", "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", "openai")
_OLLAMA = ("ollama", "http://localhost:11434/v1", "qwen2.5-coder:latest", "openai")

# Task Chains Definitions (Best-first ordered pipelines)
TASK_CHAINS: Dict[str, List[Tuple[str, str, str, str]]] = {
    "speed": [_CEREBRAS, _GROQ, _GEMINI, _OPENROUTER, _TOGETHER],
    "reasoning": [_DEEPSEEK_R1, _GEMINI, _OPENROUTER, _TOGETHER],
    "code": [_DEEPSEEK, _OPENROUTER, _SAMBANOVA, _GROQ, _OLLAMA],
    "vision": [_GEMINI, _OPENROUTER],
    "research": [_DEEPSEEK_R1, _GEMINI, _OPENROUTER, _TOGETHER],
    "agent": [_DEEPSEEK_R1, _GEMINI, _GROQ, _OLLAMA],
    "write": [_CEREBRAS, _GROQ, _TOGETHER, _OPENROUTER],
    "pentest": [_GROQ, _DEEPSEEK_R1, _TOGETHER],
    "offline": [_OLLAMA]
}

# Master list of all providers to act as absolute fallbacks
ALL_PROVIDERS = [_CEREBRAS, _GROQ, _GEMINI, _DEEPSEEK, _SAMBANOVA, _TOGETHER, _OPENROUTER, _OLLAMA]

def format_gemini_messages(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """Converts standard system/user/assistant role list to Gemini format."""
    contents = []
    system_instruction = None
    
    # Pre-process messages to combine consecutive identical roles
    processed_messages: List[Dict[str, str]] = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        
        if role == "system":
            if system_instruction is None:
                system_instruction = {"parts": [{"text": content}]}
            else:
                system_instruction["parts"][0]["text"] += "\n" + content
            continue
            
        gemini_role = "user" if role == "user" else "model"
        
        if processed_messages and processed_messages[-1]["role"] == gemini_role:
            processed_messages[-1]["content"] += "\n\n" + content
        else:
            processed_messages.append({"role": gemini_role, "content": content})
            
    for msg in processed_messages:
        contents.append({"role": msg["role"], "parts": [{"text": msg["content"]}]})
        
    # Ensure contents list is not empty
    if not contents:
        contents.append({"role": "user", "parts": [{"text": "Hello"}]})
        
    payload: Dict[str, Any] = {"contents": contents}
    if system_instruction:
        payload["systemInstruction"] = system_instruction
    return payload

def execute_request(provider: Tuple[str, str, str, str], messages: List[Dict[str, str]], max_tokens: int) -> Optional[str]:
    """Sends a completion request to a specific provider using direct HTTP client."""
    name, base_url, model, p_type = provider
    keys = get_keys_for_provider(name)
    
    # If the provider is Ollama, it doesn't need an API key
    if name == "ollama":
        key, key_idx = "ollama-local", 0
    else:
        key, key_idx = get_next_key(name, keys)
        if key == "PLACEHOLDER_NO_KEY":
            log.debug(f"Skipping {name}: no API key configured.")
            return None
            
    try:
        # Standard timeout for network requests (12 seconds connection, 25 seconds response)
        timeout = httpx.Timeout(25.0, connect=12.0)
        
        with httpx.Client(timeout=timeout) as client:
            if p_type == "openai":
                headers = {
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                }
                if name == "openrouter":
                    headers["HTTP-Referer"] = "https://github.com/m4stanuj/M4STCLAW"
                    headers["X-Title"] = "M4STCLAW Workspace"
                    
                payload = {
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.7
                }
                
                response = client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
                
                # Check for rate-limiting or credentials issues
                if response.status_code == 429:
                    set_cooldown(name, key_idx, 60.0)  # Cool down key for 1 minute
                    return None
                elif response.status_code in (401, 403):
                    set_cooldown(name, key_idx, 3600.0)  # Invalid keys cooled down for 1 hour
                    return None
                    
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
                
            elif p_type == "gemini":
                # Call Gemini generateContent API
                url = f"{base_url}/models/{model}:generateContent?key={key}"
                payload = format_gemini_messages(messages)
                payload["generationConfig"] = {
                    "maxOutputTokens": max_tokens,
                    "temperature": 0.7
                }
                
                response = client.post(url, json=payload)
                
                if response.status_code == 429:
                    set_cooldown(name, key_idx, 60.0)
                    return None
                elif response.status_code in (401, 403):
                    set_cooldown(name, key_idx, 3600.0)
                    return None
                    
                response.raise_for_status()
                data = response.json()
                candidates = data.get("candidates", [])
                if candidates:
                    return candidates[0]["content"]["parts"][0]["text"]
                return None
                
    except Exception as e:
        log.warning(f"Request failed for provider '{name}' ({model}): {e}")
        # Apply a brief cooldown on connection errors
        set_cooldown(name, key_idx, 15.0)
        return None
        
    return None

def chat_complete(messages: List[Dict[str, str]], task: str = "speed", max_tokens: int = 1024) -> str:
    """Routes completion request through task chain and falls back to other providers if needed."""
    chain = TASK_CHAINS.get(task, TASK_CHAINS["speed"])
    tried = set()
    
    # Step 1: Try providers in the active task chain
    for provider in chain:
        name = provider[0]
        tried.add(name)
        log.info(f"Attempting completion via task chain provider: '{name}' ({provider[2]})")
        
        result = execute_request(provider, messages, max_tokens)
        if result is not None:
            return result
            
    # Step 2: Task chain exhausted, fall back to any other active provider
    log.warning(f"Task chain '{task}' exhausted. Falling back to master provider list...")
    for provider in ALL_PROVIDERS:
        name = provider[0]
        if name in tried:
            continue
            
        log.info(f"Attempting master fallback provider: '{name}'")
        result = execute_request(provider, messages, max_tokens)
        if result is not None:
            return result
            
    return f"ERROR: All providers failed for task '{task}'. Please check your internet connection or API keys in .env."

async def execute_request_async(provider: Tuple[str, str, str, str], messages: List[Dict[str, str]], max_tokens: int) -> Optional[str]:
    """Sends an asynchronous completion request to a specific provider."""
    name, base_url, model, p_type = provider
    keys = get_keys_for_provider(name)
    
    if name == "ollama":
        key, key_idx = "ollama-local", 0
    else:
        key, key_idx = get_next_key(name, keys)
        if key == "PLACEHOLDER_NO_KEY":
            return None
            
    try:
        timeout = httpx.Timeout(25.0, connect=12.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            if p_type == "openai":
                headers = {
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                }
                if name == "openrouter":
                    headers["HTTP-Referer"] = "https://github.com/m4stanuj/M4STCLAW"
                    headers["X-Title"] = "M4STCLAW Workspace"
                    
                payload = {
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.7
                }
                
                response = await client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
                
                if response.status_code == 429:
                    set_cooldown(name, key_idx, 60.0)
                    return None
                elif response.status_code in (401, 403):
                    set_cooldown(name, key_idx, 3600.0)
                    return None
                    
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
                
            elif p_type == "gemini":
                url = f"{base_url}/models/{model}:generateContent?key={key}"
                payload = format_gemini_messages(messages)
                payload["generationConfig"] = {
                    "maxOutputTokens": max_tokens,
                    "temperature": 0.7
                }
                
                response = await client.post(url, json=payload)
                
                if response.status_code == 429:
                    set_cooldown(name, key_idx, 60.0)
                    return None
                elif response.status_code in (401, 403):
                    set_cooldown(name, key_idx, 3600.0)
                    return None
                    
                response.raise_for_status()
                data = response.json()
                candidates = data.get("candidates", [])
                if candidates:
                    return candidates[0]["content"]["parts"][0]["text"]
                return None
                
    except Exception as e:
        log.warning(f"Async request failed for provider '{name}' ({model}): {e}")
        set_cooldown(name, key_idx, 15.0)
        return None
    return None

async def chat_complete_async(messages: List[Dict[str, str]], task: str = "speed", max_tokens: int = 1024) -> str:
    """Asynchronously routes completion request through task chain and falls back if needed."""
    chain = TASK_CHAINS.get(task, TASK_CHAINS["speed"])
    tried = set()
    
    for provider in chain:
        name = provider[0]
        tried.add(name)
        log.info(f"Attempting async completion via task chain provider: '{name}' ({provider[2]})")
        
        result = await execute_request_async(provider, messages, max_tokens)
        if result is not None:
            return result
            
    log.warning(f"Async task chain '{task}' exhausted. Falling back to master provider list...")
    for provider in ALL_PROVIDERS:
        name = provider[0]
        if name in tried:
            continue
            
        log.info(f"Attempting async master fallback provider: '{name}'")
        result = await execute_request_async(provider, messages, max_tokens)
        if result is not None:
            return result
            
    return f"ERROR: All providers failed for task '{task}'. Please check your internet connection or API keys in .env."

async def chat_complete_stream(messages: List[Dict[str, str]], task: str = "speed", max_tokens: int = 1024):
    """Routes completion requests and yields real-time text tokens asynchronously."""
    chain = TASK_CHAINS.get(task, TASK_CHAINS["speed"])
    tried = set()
    
    for provider in chain:
        name, base_url, model, p_type = provider
        tried.add(name)
        keys = get_keys_for_provider(name)
        
        if name == "ollama":
            key, key_idx = "ollama-local", 0
        else:
            key, key_idx = get_next_key(name, keys)
            if key == "PLACEHOLDER_NO_KEY":
                continue
                
        log.info(f"Attempting async stream via provider: '{name}' ({model})")
        
        try:
            timeout = httpx.Timeout(25.0, connect=12.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                if p_type == "openai":
                    headers = {
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json"
                    }
                    if name == "openrouter":
                        headers["HTTP-Referer"] = "https://github.com/m4stanuj/M4STCLAW"
                        headers["X-Title"] = "M4STCLAW Workspace"
                        
                    payload = {
                        "model": model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": 0.7,
                        "stream": True
                    }
                    
                    async with client.stream("POST", f"{base_url}/chat/completions", headers=headers, json=payload) as response:
                        if response.status_code == 200:
                            async for line in response.aiter_lines():
                                line = line.strip()
                                if not line:
                                    continue
                                if line.startswith("data: "):
                                    data_content = line[6:]
                                    if data_content == "[DONE]":
                                        break
                                    try:
                                        chunk_data = json.loads(data_content)
                                        choices = chunk_data.get("choices", [])
                                        if choices:
                                            delta = choices[0].get("delta", {})
                                            content = delta.get("content", "")
                                            if content:
                                                yield content
                                    except Exception:
                                        pass
                            return
                        elif response.status_code == 429:
                            set_cooldown(name, key_idx, 60.0)
                        elif response.status_code in (401, 403):
                            set_cooldown(name, key_idx, 3600.0)
                            
                elif p_type == "gemini":
                    url = f"{base_url}/models/{model}:generateContent?key={key}"
                    payload = format_gemini_messages(messages)
                    payload["generationConfig"] = {
                        "maxOutputTokens": max_tokens,
                        "temperature": 0.7
                    }
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            yield candidates[0]["content"]["parts"][0]["text"]
                        return
                    elif resp.status_code == 429:
                        set_cooldown(name, key_idx, 60.0)
                    elif resp.status_code in (401, 403):
                        set_cooldown(name, key_idx, 3600.0)
                        
        except Exception as e:
            log.warning(f"Async stream failed for provider '{name}' ({model}): {e}")
            set_cooldown(name, key_idx, 15.0)
            
    yield f"ERROR: Streaming failed or all providers rate-limited. Please check keys."
