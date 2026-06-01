"""
browser_handler.py — Browser Automation Handler
=================================================
Automates browser actions using Playwright (fetching pages, click selectors,
input text, taking page screenshots). Fallbacks to HTTP client if Playwright is unavailable.
"""

import os
import re
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import httpx

log = logging.getLogger("m4stclaw.servers.browser")

# Output directory for page screenshots (sandbox-restricted)
SCREENSHOT_DIR = Path(os.path.expanduser("~/.config/m4stclaw/screenshots"))

# Playwright initialization status
_playwright_installed = False
try:
    from playwright.sync_api import sync_playwright
    _playwright_installed = True
except ImportError:
    log.warning("Playwright is not installed. Browser handler will fall back to static HTTP crawls.")

def visit_webpage(url: str, click_selector: Optional[str] = None, screenshot_name: Optional[str] = None) -> Dict[str, Any]:
    """Visits a webpage, extracts content, clicks an optional selector, and takes a screenshot."""
    result = {
        "status": "error",
        "url": url,
        "title": "",
        "content": "",
        "screenshot_path": None,
        "mode": ""
    }

    # 1. Attempt Playwright execution if available
    if _playwright_installed:
        try:
            SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            screenshot_path = None
            if screenshot_name:
                # Sanitize filename to prevent directory traversal
                safe_name = os.path.basename(screenshot_name)
                if not safe_name.lower().endswith(".png"):
                    safe_name += ".png"
                screenshot_path = SCREENSHOT_DIR / safe_name

            with sync_playwright() as p:
                log.info(f"Launching Playwright browser to visit: {url}")
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                # Navigate with a timeout of 15 seconds
                page.goto(url, timeout=15000, wait_until="load")

                result["title"] = page.title()

                # Execute optional click interaction
                if click_selector:
                    log.info(f"Clicking browser element: {click_selector}")
                    page.click(click_selector, timeout=5000)
                    page.wait_for_timeout(1000)  # Wait 1s for dynamic updates

                # Extract text
                result["content"] = page.locator("body").inner_text()

                # Take screenshot
                if screenshot_path:
                    page.screenshot(path=str(screenshot_path))
                    result["screenshot_path"] = str(screenshot_path)
                    log.info(f"Page screenshot captured at: {screenshot_path}")

                browser.close()
                result["status"] = "success"
                result["mode"] = "playwright"
                return result

        except Exception as e:
            log.error(f"Playwright browser execution failed: {e}. Falling back to static HTTP crawl.")

    # 2. Static HTTP fallback
    try:
        log.info(f"Performing static HTTP request fallback for: {url}")
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            resp = client.get(url, headers=headers)
            resp.raise_for_status()

            # Simple title extraction from raw HTML
            title = ""
            title_match = re.search(r"<title>(.*?)</title>", resp.text, re.I)
            if title_match:
                title = title_match.group(1).strip()

            # Clean HTML by stripping script, style blocks, and comments first
            html = resp.text
            html = re.sub(r"<script[^>]*>([\s\S]*?)</script>", " ", html, flags=re.I)
            html = re.sub(r"<style[^>]*>([\s\S]*?)</style>", " ", html, flags=re.I)
            html = re.sub(r"<!--([\s\S]*?)-->", " ", html)

            # Strip HTML tags and normalize spacing
            text_content = re.sub(r"<[^>]+>", " ", html)
            text_content = re.sub(r"\s+", " ", text_content).strip()

            result["title"] = title
            result["content"] = text_content[:15000]  # limit length
            result["status"] = "success"
            result["mode"] = "http_fallback"
            return result

    except Exception as e:
        result["content"] = f"ERROR: Failed to retrieve webpage contents. Details: {e}"
        return result
