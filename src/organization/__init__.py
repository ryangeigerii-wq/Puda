"""
Organization Layer - Structured Digital Archive

Purpose:
    Automatically organize verified documents into a structured archive
    with standardized folder naming and comprehensive indexing.

Folder Convention:
    {Owner}/{Year}/{DocType}/{BatchID}/
    
    Example:
    JohnDoe/2024/Invoice/batch_001/
        - invoice_001.png
        - invoice_001.json
        - invoice_001_ocr.txt
"""

from .archive import ArchiveManager, FolderStructure, DocumentArchive
from .indexer import ArchiveIndexer, SearchQuery
from .automation import OrganizationAutomation
from .pdf_merger import PDFMerger, PDFMergeAutomation
from .thumbnails import ThumbnailGenerator, ThumbnailAutomation, ThumbnailSizes

__all__ = [
    'ArchiveManager',
    'FolderStructure',
    'DocumentArchive',
    'ArchiveIndexer',
    'SearchQuery',
    'OrganizationAutomation',
    'PDFMerger',
    'PDFMergeAutomation',
    'ThumbnailGenerator',
    'ThumbnailAutomation',
    'ThumbnailSizes',
]
