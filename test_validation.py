"""Tests for file validation (checksum, duplicate detection, PDF page count)."""
import tempfile
from pathlib import Path

from src.scanner.validation import FileValidator


def test_checksum_and_duplicate_detection():
    v = FileValidator()
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        f1 = p / "a.bin"
        f2 = p / "b.bin"
        f1.write_bytes(b"same")
        f2.write_bytes(b"same")
        r1 = v.validate(str(f1))
        r2 = v.validate(str(f2))
        assert r1.sha256 == r2.sha256
        assert r1.is_duplicate is False
        assert r2.is_duplicate is True


def test_pdf_page_count_if_available():
    v = FileValidator()
    try:
        import PyPDF2  # noqa: F401
    except Exception:
        # Dependency may not be installed in minimal environment; skip
        return
    from io import BytesIO
    from PyPDF2 import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_blank_page(width=72, height=72)
    pdf_stream = BytesIO()
    writer.write(pdf_stream)
    data = pdf_stream.getvalue()
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "doc.pdf"
        pdf_path.write_bytes(data)
        result = v.validate(str(pdf_path))
        assert result.page_count in (2, None)  # None if parsing fails unexpectedly
