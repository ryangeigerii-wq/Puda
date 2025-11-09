"""Processing instrumentation utilities.

Provides decorators and helpers for timing and structured logging of processors.
"""
from __future__ import annotations

import time
import logging
from functools import wraps
from typing import Callable, Any

# Basic logging configuration (can be overridden by app)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("processing")


def time_processor(fn: Callable) -> Callable:
    """Decorator to time a processor's process() call.

    Expects signature process(self, artifact, ctx) and returns artifact.
    Stores duration_ms under artifact.metadata['processing']['timing'][processor_name].
    """
    @wraps(fn)
    def wrapper(self, artifact, ctx):  # type: ignore
        start = time.perf_counter()
        result = fn(self, artifact, ctx)
        duration_ms = int((time.perf_counter() - start) * 1000)
        try:
            artifact.metadata.setdefault('processing', {})
            timing = artifact.metadata['processing'].setdefault('timing', {})
            timing[self.name] = duration_ms
        except Exception:  # pragma: no cover
            pass
        logger.info("processor=%s page_id=%s duration_ms=%d", getattr(self, 'name', fn.__name__), getattr(artifact, 'page_id', 'unknown'), duration_ms)
        return result
    return wrapper


def instrument_class(cls: Any) -> Any:
    """Class decorator to automatically time process() if present."""
    if hasattr(cls, 'process') and callable(getattr(cls, 'process')):
        setattr(cls, 'process', time_processor(getattr(cls, 'process')))
    return cls
