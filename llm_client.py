"""Centralized Gemini client with singleton model, basic caching, and quota-safe retries.

Usage:
    from llm_client import generate_text
    text = generate_text(prompt)

Environment:
    GEMINI_API_KEY or GOOGLE_API_KEY must be set.
Optional env toggles:
    GEMINI_MODEL (default gemini-1.5-flash)
    LLM_CACHE_TTL_SECONDS (default 300)
"""
from __future__ import annotations
import os, time, threading, hashlib
from typing import Optional
import google.generativeai as genai

_LOCK = threading.Lock()
_MODEL = None
_MODEL_NAME = None
_CACHE: dict[str, tuple[float, str]] = {}
_DEFAULT_TTL = int(os.getenv("LLM_CACHE_TTL_SECONDS", "300"))


def _init_model(model_name: str):
    global _MODEL, _MODEL_NAME
    if _MODEL is not None and _MODEL_NAME == model_name:
        return _MODEL
    with _LOCK:
        if _MODEL is not None and _MODEL_NAME == model_name:
            return _MODEL
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return None
        try:
            genai.configure(api_key=api_key)
            _MODEL = genai.GenerativeModel(model_name=model_name)
            _MODEL_NAME = model_name
        except Exception as e:
            print(f"Gemini init failed: {e}")
            _MODEL = None
        return _MODEL


def _cache_key(prompt: str, model_name: str) -> str:
    h = hashlib.sha256()
    h.update(model_name.encode())
    h.update(prompt.encode())
    return h.hexdigest()


def generate_text(prompt: str, *, model_name: Optional[str] = None, use_cache: bool = True, ttl: Optional[int] = None, retries: int = 1) -> str:
    """Generate text with caching + basic quota/backoff handling.

    Args:
        prompt: prompt string
        model_name: override model name (env GEMINI_MODEL else gemini-1.5-flash)
        use_cache: if True, return cached response for identical prompt within TTL
        ttl: cache time-to-live seconds
        retries: additional retry attempts on transient/quota errors
    """
    model_name = model_name or os.getenv("GEMINI_MODEL") or "gemini-1.5-flash"
    ttl = _DEFAULT_TTL if ttl is None else ttl

    if use_cache:
        ck = _cache_key(prompt, model_name)
        cached = _CACHE.get(ck)
        if cached and (time.time() - cached[0]) < ttl:
            return cached[1]

    model = _init_model(model_name)
    if not model:
        return "LLM unavailable (API key not configured)."

    last_err = None
    for attempt in range(retries + 1):
        try:
            resp = model.generate_content(prompt)
            text = (getattr(resp, 'text', '') or '').strip()
            if not text:
                text = "(No content returned from model)"
            if use_cache:
                _CACHE[ck] = (time.time(), text)
            return text
        except Exception as e:
            msg = str(e).lower()
            last_err = e
            if 'quota' in msg or '429' in msg or 'rate' in msg:
                # Exponential backoff
                sleep_for = 1.5 ** attempt
                time.sleep(sleep_for)
                continue
            break
    # Fallback message with minimal leakage
    return "Service load is high right now (quota). Please retry shortly." if last_err else "Error generating response."  # noqa
