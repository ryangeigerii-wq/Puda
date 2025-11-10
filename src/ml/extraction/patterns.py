"""Pattern-based entity detection utilities.

Provides lightweight regex-based extraction for common document fields:
- Dates
- Monetary amounts
- Invoice numbers
- Emails
- Phone numbers

Designed to complement model BIO-tag extraction. All functions return
lists of dictionaries with a common shape so they can be merged easily.
"""
from __future__ import annotations
import re
from typing import List, Dict

DATE_PATTERNS = [
    # ISO / standard numeric
    r"\b(\d{4}-\d{2}-\d{2})\b",
    r"\b(\d{2}/\d{2}/\d{4})\b",
    r"\b(\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4})\b",
    # Month name (English/French variants), e.g., Nov 8, 2025 / 8 Nov 2025
    r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|Janv|Fév|Fev|Mars|Avr|Mai|Juin|Juil|Août|Aout|Sep|Oct|Nov|Déc|Dec)\.?(?:\s+\d{1,2},?\s+\d{4}|\s+\d{4}|\s+\d{1,2}\s+\d{4}))\b",
]

AMOUNT_PATTERNS = [
    r"\b(?:USD|CAD|EUR|GBP|\$|€|£)\s?[+-]?\d{1,3}(?:[\,\s]\d{3})*(?:\.\d{2})?\b",
    r"\b[+-]?\d{1,3}(?:[\,\s]\d{3})*(?:\.\d{2})?\s?(?:USD|CAD|EUR|GBP)\b",
]

INVOICE_PATTERNS = [
    r"\bINV[- ]?\d{4,}\b",
    r"\bInvoice\s*#?:?\s*[A-Za-z0-9-]{4,}\b",
]

EMAIL_PATTERN = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
PHONE_PATTERN = r"\b(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{3}\)?[\s-]?)?\d{3}[\s-]?\d{4}\b"

_COMPILED = {
    "DATE": [re.compile(p, re.IGNORECASE) for p in DATE_PATTERNS],
    "AMOUNT": [re.compile(p) for p in AMOUNT_PATTERNS],
    "INVOICE": [re.compile(p, re.IGNORECASE) for p in INVOICE_PATTERNS],
    "EMAIL": [re.compile(EMAIL_PATTERN)],
    "PHONE": [re.compile(PHONE_PATTERN)],
}


def _unique_preserve_order(values: List[str]) -> List[str]:
    seen = set()
    out = []
    for v in values:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def extract_with_patterns(text: str) -> Dict[str, List[Dict]]:
    """Run all pattern detectors over the text.

    Returns a dict mapping entity type to list of {text, confidence, source}.
    Confidence here is heuristic (0.85 base for matches). Can be adjusted later.
    """
    results: Dict[str, List[Dict]] = {k: [] for k in _COMPILED.keys()}
    for etype, patterns in _COMPILED.items():
        matches: List[str] = []
        for pat in patterns:
            matches.extend(m.group(0).strip() for m in pat.finditer(text))
        matches = _unique_preserve_order(matches)
        for m in matches:
            results[etype].append({"text": m, "confidence": 0.85, "source": "pattern"})
    return {k: v for k, v in results.items() if v}

__all__ = ["extract_with_patterns"]
