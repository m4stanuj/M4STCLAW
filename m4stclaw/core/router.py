"""
router.py — Task Router
=========================
Analyzes incoming queries and classifies them into one of the 9 specialized task chains.
Enforces whole-word matching to prevent substring collision bugs.
"""

import re
import logging
from typing import Dict, List

log = logging.getLogger("m4stclaw.core.router")

VALID_TASKS = [
    "speed", "reasoning", "code", "vision", "research",
    "agent", "write", "pentest", "offline"
]

TASK_KEYWORDS: Dict[str, List[str]] = {
    "speed": [
        "quick", "fast", "time", "date", "hello", "hi", "convert", "translate",
        "calculate", "tldr", "short", "simple", "brief", "seedha", "ek line"
    ],
    "reasoning": [
        "think", "explain", "why", "logic", "reason", "math", "proof", "derivation",
        "compare", "pros and cons", "analysis", "step-by-step", "kyun", "kaise", "samjhao"
    ],
    "code": [
        "code", "script", "function", "bug", "error", "exception", "class", "refactor",
        "compile", "react", "html", "css", "js", "ts", "python", "java", "c++", "rust",
        "database", "sql", "api", "git", "diff", "merge", "pull request", "banao", "likho code"
    ],
    "vision": [
        "image", "screenshot", "ocr", "read screen", "describe image", "visual",
        "look", "see", "show", "gui", "dekho", "kya dikh raha"
    ],
    "research": [
        "research", "latest", "trends", "news", "articles", "deep dive", "gather info",
        "web search", "investigate", "market", "competitor", "dhundo", "pata lagao"
    ],
    "agent": [
        "automate", "schedule", "cron", "workflow", "run task", "background", "loop",
        "pipeline", "orchestrate", "sequence", "khud karo", "automate karo"
    ],
    "write": [
        "write", "essay", "draft", "email", "summary", "article", "blog", "compose",
        "document", "readme", "markdown", "text", "paraphrase", "likho", "report"
    ],
    "pentest": [
        "scan", "nmap", "nuclei", "shodan", "vulnerability", "exploit", "cve", "recon",
        "security audit", "port", "target", "pentest", "hacker", "osint", "injection", "xss"
    ],
    "offline": [
        "offline", "local", "ollama", "llama", "qwen", "mistral-local", "no-internet",
        "disconnect", "local run", "offline mode"
    ]
}

def classify_task(prompt: str) -> str:
    """Classifies a user prompt into one of the 9 task types using word boundaries."""
    text = prompt.lower()
    # Normalize punctuation and split into unique words
    words = set(re.sub(r'[^\w\s]', ' ', text).split())
    scores = {task: 0 for task in VALID_TASKS}
    
    for task, keywords in TASK_KEYWORDS.items():
        for kw in keywords:
            # For multi-word phrases (e.g. "deep dive", "pull request")
            if " " in kw:
                if kw in text:
                    scores[task] += 2
            else:
                # Check for exact word boundaries
                if kw in words:
                    scores[task] += 1
                    
    best_task = max(scores, key=scores.get)
    if scores[best_task] > 0:
        log.info(f"Classified task: '{best_task}' (Score: {scores[best_task]})")
        return best_task
        
    return "speed"  # default to speed chain for general queries
