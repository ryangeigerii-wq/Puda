"""Summarization utilities.

Provides a best-effort summarization function. Attempts to load a
transformer summarization pipeline (e.g., 'google/mt5-small' or
'facebook/bart-base'); if unavailable, falls back to a heuristic summary.
"""
from __future__ import annotations
from typing import Dict
import logging

logger = logging.getLogger(__name__)

_SUMMARIZER = None

_TRANSFORMER_MODELS = [
    "facebook/bart-base",
    "sshleifer/distilbart-cnn-12-6",
    "google/mt5-small",
]


def _load_transformer_summarizer():  # pragma: no cover (heavy path)
    global _SUMMARIZER
    if _SUMMARIZER is not None:
        return _SUMMARIZER
    try:
        from transformers import pipeline  # type: ignore
    except Exception:
        logger.warning("Transformers summarization pipeline unavailable; using fallback")
        return None
    for model_name in _TRANSFORMER_MODELS:
        try:
            _SUMMARIZER = pipeline("summarization", model=model_name)
            logger.info(f"Loaded summarization model: {model_name}")
            return _SUMMARIZER
        except Exception:
            continue
    logger.warning("No summarization model could be loaded; fallback engaged")
    return None


def _fallback_summary(text: str, max_sentences: int = 3) -> str:
    import re
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    # Keep moderately sized sentences
    filtered = [s for s in sentences if 20 <= len(s) <= 300]
    if not filtered:
        filtered = sentences[:max_sentences]
    summary = " ".join(filtered[:max_sentences])
    return summary[:600]


def summarize(text: str) -> Dict:
    """Generate a summary dict with text, confidence, method.

    Confidence heuristic:
      - transformer: 0.75
      - fallback: 0.40 (adjust upward once validated)
    """
    if not text.strip():
        return {"text": "", "confidence": 0.0, "method": "none"}
    summarizer = _load_transformer_summarizer()
    if summarizer:
        try:
            result = summarizer(text[:4000], max_length=130, min_length=30, do_sample=False)
            if isinstance(result, list) and result:
                summary_text = result[0].get("summary_text", "").strip()
            else:
                summary_text = ""
            return {"text": summary_text, "confidence": 0.75, "method": "transformer"}
        except Exception as e:  # pragma: no cover
            logger.warning(f"Transformer summarization failed: {e}; using fallback")
    # Fallback
    return {"text": _fallback_summary(text), "confidence": 0.40, "method": "fallback"}

__all__ = ["summarize"]
