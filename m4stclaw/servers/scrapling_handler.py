"""
scrapling_handler.py — Anti-Bot Scraper
========================================
Retrieves raw web content while bypassing basic anti-bot blockers using header spoofing.
"""

import re
import random
import logging
import httpx
from typing import Dict, Any

log = logging.getLogger("m4stclaw.servers.scrapling")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

def extract_clean_web_text(url: str) -> Dict[str, Any]:
    """Retrieves webpage, parses text, and strips HTML script/style boilerplate."""
    result = {
        "status": "error",
        "url": url,
        "content": "",
        "headers_used": {}
    }
    
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    
    result["headers_used"] = headers
    
    try:
        log.info(f"Crawling URL: {url}")
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            
            if resp.status_code != 200:
                result["content"] = f"ERROR: Crawl failed with HTTP Status Code {resp.status_code}"
                return result
                
            html = resp.text
            
            # 1. Strip script and style blocks
            html = re.sub(r"<script[^>]*>([\s\S]*?)</script>", " ", html, flags=re.I)
            html = re.sub(r"<style[^>]*>([\s\S]*?)</style>", " ", html, flags=re.I)
            
            # 2. Strip comments
            html = re.sub(r"<!--([\s\S]*?)-->", " ", html)
            
            # 3. Strip tags and keep plain text
            text = re.sub(r"<[^>]+>", " ", html)
            
            # 4. Normalize whitespaces
            text = re.sub(r"\s+", " ", text).strip()
            
            result["content"] = text
            result["status"] = "success"
            
    except Exception as e:
        log.error(f"Scrapling failed: {e}")
        result["content"] = f"ERROR: Scraper failed to resolve webpage: {e}"
        
    return result
