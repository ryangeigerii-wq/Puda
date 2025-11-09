"""
Feedback Collection and Storage

Captures structured operator feedback for model retraining and quality improvement.
"""

import json
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List


class IssueCategory(Enum):
    """Categories of issues found during QC."""
    OCR_ERROR = "ocr_error"                    # OCR misread text
    CLASSIFICATION_ERROR = "classification_error"  # Wrong document type
    FIELD_EXTRACTION_ERROR = "field_extraction_error"  # Wrong/missing field
    FIELD_PARSING_ERROR = "field_parsing_error"  # Extracted but wrong format
    LAYOUT_DETECTION_ERROR = "layout_detection_error"  # Missed tables/sections
    IMAGE_QUALITY = "image_quality"            # Poor scan quality
    DOCUMENT_VARIATION = "document_variation"  # Unexpected format variant
    MULTI_PAGE_ERROR = "multi_page_error"      # Multi-page handling issue
    OTHER = "other"


@dataclass
class FeedbackEntry:
    """
    Structured feedback from operator verification.
    
    Contains original extraction results, operator corrections,
    issue categorization, and metadata for ML retraining.
    """
    timestamp: float
    task_id: str
    page_id: str
    batch_id: str
    operator_id: str
    
    # Classification feedback
    original_doc_type: str
    corrected_doc_type: str
    classification_confidence: float
    
    # Field extraction feedback
    original_fields: Dict[str, Any]
    corrected_fields: Dict[str, Any]
    field_corrections: List[Dict[str, Any]]
    avg_field_confidence: float
    
    # Issue categorization
    issue_categories: List[IssueCategory]
    severity: str
    
    # Operator assessment
    operator_confidence: float
    time_spent_seconds: int
    notes: Optional[str] = None
    
    # Outcome
    approved: bool = False
    escalated: bool = False
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['issue_categories'] = [cat.value for cat in self.issue_categories]
        data['timestamp_iso'] = datetime.fromtimestamp(self.timestamp).isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'FeedbackEntry':
        """Create from dictionary."""
        # Convert issue categories back to enum
        if 'issue_categories' in data:
            data['issue_categories'] = [
                IssueCategory(cat) for cat in data['issue_categories']
            ]
        # Remove computed field
        data.pop('timestamp_iso', None)
        return cls(**data)


class FeedbackCollector:
    """
    Collects and stores operator feedback for model improvement.
    
    Features:
    - Append-only JSONL storage
    - Daily log rotation
    - Export for ML training pipeline
    - Operator performance analytics
    """
    
    def __init__(
        self,
        feedback_dir: str = "data/feedback",
        daily_rotation: bool = True
    ):
        """
        Initialize feedback collector.
        
        Args:
            feedback_dir: Directory for feedback logs
            daily_rotation: Enable daily log file rotation
        """
        self.feedback_dir = Path(feedback_dir)
        self.feedback_dir.mkdir(parents=True, exist_ok=True)
        self.daily_rotation = daily_rotation
    
    def _get_log_path(self) -> Path:
        """Get current log file path."""
        if self.daily_rotation:
            date_str = datetime.now().strftime("%Y-%m-%d")
            return self.feedback_dir / f"qc_feedback_{date_str}.jsonl"
        return self.feedback_dir / "qc_feedback.jsonl"
    
    def add_entry(self, entry: FeedbackEntry):
        """
        Add feedback entry to log.
        
        Args:
            entry: Feedback entry to add
        """
        log_path = self._get_log_path()
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry.to_dict()) + '\n')
        except Exception as e:
            print(f"Warning: Failed to write feedback: {e}")
    
    def load_entries(
        self,
        days: Optional[int] = None,
        operator_id: Optional[str] = None
    ) -> List[FeedbackEntry]:
        """
        Load feedback entries with optional filters.
        
        Args:
            days: Load entries from last N days (None = all)
            operator_id: Filter by operator
            
        Returns:
            List of feedback entries
        """
        entries = []
        
        # Determine which log files to read
        if days and self.daily_rotation:
            # Read last N days of logs
            log_files = []
            for i in range(days):
                date = datetime.now()
                from datetime import timedelta
                date = date - timedelta(days=i)
                date_str = date.strftime("%Y-%m-%d")
                log_path = self.feedback_dir / f"qc_feedback_{date_str}.jsonl"
                if log_path.exists():
                    log_files.append(log_path)
        else:
            # Read all log files
            log_files = list(self.feedback_dir.glob("qc_feedback*.jsonl"))
        
        # Parse entries
        for log_file in log_files:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            entry = FeedbackEntry.from_dict(data)
                            
                            # Apply filters
                            if operator_id and entry.operator_id != operator_id:
                                continue
                            
                            entries.append(entry)
            except Exception as e:
                print(f"Warning: Failed to load feedback from {log_file}: {e}")
        
        return entries
    
    def get_operator_stats(self, operator_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get operator performance statistics.
        
        Args:
            operator_id: Operator identifier
            days: Period to analyze (days)
            
        Returns:
            Statistics dictionary
        """
        entries = self.load_entries(days=days, operator_id=operator_id)
        
        if not entries:
            return {
                'operator_id': operator_id,
                'total_verifications': 0
            }
        
        stats = {
            'operator_id': operator_id,
            'total_verifications': len(entries),
            'approved_count': sum(1 for e in entries if e.approved),
            'rejected_count': sum(1 for e in entries if not e.approved and not e.escalated),
            'escalated_count': sum(1 for e in entries if e.escalated),
            'total_corrections': sum(len(e.field_corrections) for e in entries),
            'avg_time_seconds': sum(e.time_spent_seconds for e in entries) / len(entries),
            'avg_confidence': sum(e.operator_confidence for e in entries) / len(entries),
            'issue_categories': {},
            'doc_types_verified': {},
            'corrections_by_field': {},
        }
        
        # Count issue categories
        for entry in entries:
            for category in entry.issue_categories:
                cat_name = category.value
                stats['issue_categories'][cat_name] = stats['issue_categories'].get(cat_name, 0) + 1
        
        # Count document types
        for entry in entries:
            doc_type = entry.corrected_doc_type
            stats['doc_types_verified'][doc_type] = stats['doc_types_verified'].get(doc_type, 0) + 1
        
        # Count corrections by field
        for entry in entries:
            for correction in entry.field_corrections:
                field_name = correction['field']
                stats['corrections_by_field'][field_name] = stats['corrections_by_field'].get(field_name, 0) + 1
        
        return stats
    
    def get_global_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get global feedback statistics.
        
        Args:
            days: Period to analyze (days)
            
        Returns:
            Global statistics dictionary
        """
        entries = self.load_entries(days=days)
        
        if not entries:
            return {'total_entries': 0}
        
        stats = {
            'total_entries': len(entries),
            'total_operators': len(set(e.operator_id for e in entries)),
            'approved_rate': sum(1 for e in entries if e.approved) / len(entries),
            'escalated_rate': sum(1 for e in entries if e.escalated) / len(entries),
            'avg_time_seconds': sum(e.time_spent_seconds for e in entries) / len(entries),
            'total_corrections': sum(len(e.field_corrections) for e in entries),
            'issue_categories': {},
            'classification_errors': 0,
            'field_extraction_errors': 0,
            'by_severity': {},
            'by_doc_type': {},
        }
        
        # Count issue categories
        for entry in entries:
            for category in entry.issue_categories:
                cat_name = category.value
                stats['issue_categories'][cat_name] = stats['issue_categories'].get(cat_name, 0) + 1
        
        # Count classification errors
        stats['classification_errors'] = sum(
            1 for e in entries if e.original_doc_type != e.corrected_doc_type
        )
        
        # Count field extraction errors
        stats['field_extraction_errors'] = sum(
            1 for e in entries if len(e.field_corrections) > 0
        )
        
        # Count by severity
        for entry in entries:
            severity = entry.severity
            stats['by_severity'][severity] = stats['by_severity'].get(severity, 0) + 1
        
        # Count by doc type
        for entry in entries:
            doc_type = entry.corrected_doc_type
            stats['by_doc_type'][doc_type] = stats['by_doc_type'].get(doc_type, 0) + 1
        
        return stats
    
    def export_for_training(
        self,
        output_path: str,
        min_operator_confidence: float = 0.8,
        approved_only: bool = True
    ) -> int:
        """
        Export high-quality feedback for ML model retraining.
        
        Args:
            output_path: Path to output training data file
            min_operator_confidence: Minimum operator confidence threshold
            approved_only: Only export approved verifications
            
        Returns:
            Number of entries exported
        """
        entries = self.load_entries()
        
        # Filter high-quality entries
        training_data = []
        for entry in entries:
            if approved_only and not entry.approved:
                continue
            if entry.operator_confidence < min_operator_confidence:
                continue
            
            # Format for ML training
            training_example = {
                'page_id': entry.page_id,
                'doc_type': entry.corrected_doc_type,
                'fields': entry.corrected_fields,
                'classification_was_correct': entry.original_doc_type == entry.corrected_doc_type,
                'field_corrections_made': len(entry.field_corrections) > 0,
                'operator_confidence': entry.operator_confidence,
                'original_classification_confidence': entry.classification_confidence,
                'original_field_confidence': entry.avg_field_confidence,
            }
            training_data.append(training_example)
        
        # Write to output file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for example in training_data:
                f.write(json.dumps(example) + '\n')
        
        return len(training_data)
