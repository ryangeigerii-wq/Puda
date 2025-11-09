"""Data Ingestion Layer

Purpose: Capture and version every page produced by the scanning workflow.
This package provides abstractions to record page-level artifacts, maintain
version history, and ensure integrity via content hashing.
"""

from .ingestion import PageVersion, PageCapture, IngestionManager  # noqa: F401
