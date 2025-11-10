"""Entity extraction orchestrator.

Combines model BIO-tag outputs with pattern-based extraction and (optionally)
spaCy NER if available. The aim is to produce a unified list of entities with
consistent structure that downstream consumers can rely on.
"""
from __future__ import annotations
from typing import Dict, List, Any
import logging

from .patterns import extract_with_patterns

logger = logging.getLogger(__name__)

try:
    import spacy  # type: ignore
    _HAVE_SPACY = True
except Exception:  # pragma: no cover
    _HAVE_SPACY = False

_SPACY_MODELS = [
    "en_core_web_sm",
    "fr_core_news_sm",
]

_loaded_spacy = None


def _load_spacy_model() -> Any:
    global _loaded_spacy
    if _loaded_spacy is not None:
        return _loaded_spacy
    if not _HAVE_SPACY:
        return None
    for name in _SPACY_MODELS:
        try:
            _loaded_spacy = spacy.load(name)
            logger.info(f"Loaded spaCy model: {name}")
            return _loaded_spacy
        except Exception:
            continue
    logger.warning("No spaCy model available; skipping spaCy NER.")
    return None


def _spacy_entities(text: str) -> Dict[str, List[Dict]]:
    nlp = _load_spacy_model()
    if not nlp:
        return {}
    doc = nlp(text)
    out: Dict[str, List[Dict]] = {}
    for ent in doc.ents:
        etype = ent.label_.upper()
        # Map spaCy labels to our canonical types where practical
        mapping = {
            "DATE": "DATE",
            "MONEY": "AMOUNT",
            "ORG": "ORG",
            "PERSON": "NAME",
            "GPE": "ADDR",
            "LOC": "ADDR",
        }
        canonical = mapping.get(etype)
        if not canonical:
            continue
        out.setdefault(canonical, []).append({
            "text": ent.text,
            "confidence": 0.80,  # heuristic for spaCy baseline
            "source": "spacy"
        })
    return out


def merge_entities(base: Dict[str, List[Dict]], *others: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
    merged: Dict[str, List[Dict]] = {k: list(v) for k, v in base.items()}
    for other in others:
        for etype, ents in other.items():
            merged.setdefault(etype, []).extend(ents)
    # Deduplicate by (text, source)
    for etype, ents in merged.items():
        seen = set()
        unique = []
        for e in ents:
            key = (e["text"].strip(), e.get("source"))
            if key not in seen:
                seen.add(key)
                unique.append(e)
        merged[etype] = unique
    # Sort each entity list by descending confidence
    for etype, ents in merged.items():
        ents.sort(key=lambda x: x.get("confidence", 0.0), reverse=True)
    return {k: v for k, v in merged.items() if v}


def extract_entities(text: str, model_entities: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
    """High-level extraction entry point.

    Parameters
    ----------
    text: Full document text.
    model_entities: Output of model._extract_entities converted to
        {"TYPE": [{"text":..., "confidence":...}, ...]} form.

    Returns
    -------
    Dict mapping entity type to unified list of entity dicts with fields:
      - text
      - confidence
      - source (pattern|model|spacy)
    """
    pattern_entities = extract_with_patterns(text)
    # Add source flag to model entities
    normalized_model = {
        k: [dict(e, source="model") for e in v]
        for k, v in model_entities.items()
    }
    spacy_ent = _spacy_entities(text)
    merged = merge_entities(normalized_model, pattern_entities, spacy_ent)
    return merged

__all__ = ["extract_entities"]
