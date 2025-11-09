"""
Quality Control (QC) Layer for Human Verification and Feedback

This module provides human-in-the-loop verification for documents routed
to QC queue or manual review, capturing operator feedback for model improvement.
"""

from .queue import QCQueue, QCTask, TaskStatus
from .interface import QCInterface
from .feedback import FeedbackCollector, FeedbackEntry

__all__ = [
    'QCQueue',
    'QCTask',
    'TaskStatus',
    'QCInterface',
    'FeedbackCollector',
    'FeedbackEntry',
]
