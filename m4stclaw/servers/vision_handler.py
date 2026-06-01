"""
vision_handler.py — Vision Analysis Handler
============================================
Captures screen / analyzes screenshots using Pillow, OCR (pytesseract),
and sends to Gemini multimodal vision models or local Ollama vision fallbacks.
"""

import os
import base64
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from PIL import ImageGrab

log = logging.getLogger("m4stclaw.servers.vision")

SCREENSHOT_DIR = Path("C:/Users/Administrator/.gemini/antigravity-ide/scratch/screenshots")

# OCR engine availability
_ocr_available = False
try:
    import pytesseract
    _ocr_available = True
except ImportError:
    log.warning("pytesseract not installed. Vision handler will run without local OCR extraction.")

def capture_primary_screen(output_name: str = "primary_screen.png") -> Path:
    """Takes a screenshot of the primary display monitor."""
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SCREENSHOT_DIR / output_name
    
    # Capture display using Pillow
    img = ImageGrab.grab()
    img.save(out_path)
    log.info(f"Monitor screen captured: {out_path}")
    return out_path

def perform_ocr(img_path: Path) -> str:
    """Extracts text from the image using local Tesseract engine."""
    if not _ocr_available:
        return "OCR unavailable: pytesseract module is not loaded."
    try:
        from PIL import Image
        img = Image.open(img_path)
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception as e:
        log.error(f"OCR processing failed: {e}")
        return f"OCR processing failed: {e}"

def analyze_image(prompt: str, image_path: Optional[str] = None, use_ollama: bool = False) -> Dict[str, Any]:
    """Analyzes an image/screenshot with a prompt using Gemini or local Ollama."""
    result = {
        "status": "error",
        "ocr_text": "",
        "analysis": "",
        "image_path": ""
    }
    
    # Capture screen if no path provided
    if not image_path:
        try:
            img_path = capture_primary_screen()
        except Exception as e:
            result["analysis"] = f"ERROR: Failed to capture screen: {e}"
            return result
    else:
        img_path = Path(image_path)
        if not img_path.exists():
            result["analysis"] = f"ERROR: Image path not found: {image_path}"
            return result
            
    result["image_path"] = str(img_path.resolve())
    
    # 1. Execute local OCR
    if _ocr_available:
        result["ocr_text"] = perform_ocr(img_path)
        
    # 2. Encode image to base64
    try:
        with open(img_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
    except Exception as e:
        result["analysis"] = f"ERROR: Failed to read image: {e}"
        return result
        
    # 3. Call Cloud Gemini or Local Ollama
    if use_ollama:
        # Call local Ollama LLaVA/vision model
        try:
            import httpx
            log.info("Sending image to local Ollama vision model...")
            payload = {
                "model": "llava:latest",
                "prompt": prompt,
                "images": [encoded_image],
                "stream": False
            }
            resp = httpx.post("http://localhost:11434/api/generate", json=payload, timeout=45.0)
            resp.raise_for_status()
            result["analysis"] = resp.json().get("response", "")
            result["status"] = "success"
        except Exception as e:
            log.error(f"Ollama vision query failed: {e}")
            result["analysis"] = f"Ollama vision execution failed: {e}"
    else:
        # Call Google Gemini API directly using our fallback config keys
        from m4stclaw.core.config import get_keys_for_provider, get_next_key
        gemini_keys = get_keys_for_provider("gemini")
        key, key_idx = get_next_key("gemini", gemini_keys)
        
        if key == "PLACEHOLDER_NO_KEY":
            result["analysis"] = "ERROR: No Gemini API Key configured for vision task."
            return result
            
        try:
            import httpx
            log.info("Sending image to Gemini vision API...")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
            
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
                            {
                                "inlineData": {
                                    "mimeType": "image/png",
                                    "data": encoded_image
                                }
                            }
                        ]
                    }
                ]
            }
            
            resp = httpx.post(url, json=payload, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                result["analysis"] = candidates[0]["content"]["parts"][0]["text"]
                result["status"] = "success"
            else:
                result["analysis"] = "Gemini returned empty candidate choices."
        except Exception as e:
            log.error(f"Gemini vision API failed: {e}")
            result["analysis"] = f"Gemini vision API failed: {e}"
            
    return result
