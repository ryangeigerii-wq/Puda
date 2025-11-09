"""
Test QC Web Interface

Creates sample tasks and launches QC web application for testing.
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.qc.queue import QCQueue, QCTask, TaskStatus, TaskPriority


def create_sample_tasks():
    """Create sample QC tasks for testing."""
    queue = QCQueue()
    
    # Sample task 1: Invoice with low field confidence
    task1 = QCTask(
        task_id="test_invoice_001",
        page_id="page_invoice_001",
        batch_id="batch_001",
        doc_type="invoice",
        severity="qc",
        status=TaskStatus.PENDING,
        priority=TaskPriority.MEDIUM,
        created_at=time.time(),
        metadata={
            "original_doc_type": "invoice",
            "original_fields": {
                "invoice_number": "INV-2024-001",
                "total_amount": "1,234.56",
                "invoice_date": "2024-11-08"
            },
            "classification_confidence": 0.82,
            "avg_field_confidence": 0.61,
            "field_confidences": {
                "invoice_number": 0.85,
                "total_amount": 0.42,
                "invoice_date": 0.56
            },
            "reasons": [
                "field_conf_low:0.61",
                "missing_fields:vendor_name"
            ],
            "thresholds_used": {
                "classification_threshold": 0.55,
                "field_threshold": 0.65
            }
        },
        image_path="data/scans/test_invoice.png",
        ocr_text="""INVOICE
Invoice Number: INV-2024-001
Date: November 8, 2024

Total Amount: $1,234.56

Please remit payment within 30 days.
""",
        extracted_fields={
            "invoice_number": "INV-2024-001",
            "total_amount": "1,234.56",
            "invoice_date": "2024-11-08"
        }
    )
    
    # Sample task 2: ID document with classification uncertainty
    task2 = QCTask(
        task_id="test_id_002",
        page_id="page_id_002",
        batch_id="batch_001",
        doc_type="id",
        severity="manual",
        status=TaskStatus.PENDING,
        priority=TaskPriority.HIGH,
        created_at=time.time(),
        metadata={
            "original_doc_type": "id",
            "original_fields": {
                "id_number": "DL123456789",
                "name": "John Doe",
                "dob": "1990-05-15"
            },
            "classification_confidence": 0.38,
            "avg_field_confidence": 0.72,
            "field_confidences": {
                "id_number": 0.88,
                "name": 0.65,
                "dob": 0.63
            },
            "reasons": [
                "classification_conf_very_low:0.38"
            ],
            "thresholds_used": {
                "classification_threshold": 0.55,
                "classification_manual_threshold": 0.35
            }
        },
        image_path="data/scans/test_id.png",
        ocr_text="""DRIVER LICENSE
Name: John Doe
License Number: DL123456789
DOB: 05/15/1990
Expires: 05/15/2028
""",
        extracted_fields={
            "id_number": "DL123456789",
            "name": "John Doe",
            "dob": "1990-05-15"
        }
    )
    
    # Sample task 3: Form with missing fields
    task3 = QCTask(
        task_id="test_form_003",
        page_id="page_form_003",
        batch_id="batch_002",
        doc_type="form",
        severity="qc",
        status=TaskStatus.PENDING,
        priority=TaskPriority.MEDIUM,
        created_at=time.time(),
        metadata={
            "original_doc_type": "form",
            "original_fields": {},
            "classification_confidence": 0.67,
            "avg_field_confidence": None,
            "field_confidences": {},
            "reasons": [
                "missing_all_required_fields"
            ],
            "thresholds_used": {
                "field_threshold": 0.65
            }
        },
        image_path="data/scans/test_form.png",
        ocr_text="""APPLICATION FORM
Please complete all sections.

Section A: Personal Information
[Blank]

Section B: Contact Details
[Blank]
""",
        extracted_fields={}
    )
    
    print("Creating sample tasks...")
    queue.add_task(task1)
    print(f"✓ Created task: {task1.task_id} (Invoice, QC)")
    
    queue.add_task(task2)
    print(f"✓ Created task: {task2.task_id} (ID, Manual Review)")
    
    queue.add_task(task3)
    print(f"✓ Created task: {task3.task_id} (Form, QC)")
    
    print(f"\nTotal tasks in queue: {len(queue.tasks)}")
    print("\nQueue statistics:")
    stats = queue.get_queue_stats()
    print(f"  Pending: {stats['pending']}")
    print(f"  By severity: {stats['by_severity']}")
    print(f"  By priority: {stats['by_priority']}")


if __name__ == '__main__':
    print("=" * 60)
    print("QC Web Interface Test Setup")
    print("=" * 60)
    print()
    
    # Create sample tasks
    create_sample_tasks()
    
    print("\n" + "=" * 60)
    print("To start the QC web interface, run:")
    print("  python qc_app.py --port 8081")
    print("\nThen open: http://127.0.0.1:8081")
    print("=" * 60)
