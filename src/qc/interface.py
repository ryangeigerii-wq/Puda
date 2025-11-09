"""
QC Verification Interface

Provides interface for operators to review and verify documents,
correct field extractions, and provide structured feedback.
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from .queue import QCQueue, QCTask, TaskStatus, TaskPriority
from .feedback import FeedbackCollector, FeedbackEntry, IssueCategory


@dataclass
class FieldCorrection:
    """Represents a field correction made by operator."""
    field_name: str
    original_value: Any
    corrected_value: Any
    confidence_rating: float  # Operator's confidence in correction (0-1)
    notes: Optional[str] = None


@dataclass
class VerificationResult:
    """Result of QC verification."""
    task_id: str
    operator_id: str
    approved: bool
    corrected_doc_type: Optional[str] = None
    field_corrections: Optional[List[FieldCorrection]] = None
    issue_categories: Optional[List[IssueCategory]] = None
    operator_confidence: float = 1.0  # Overall confidence in verification
    time_spent_seconds: int = 0
    notes: Optional[str] = None
    escalate: bool = False
    
    def __post_init__(self):
        if self.field_corrections is None:
            self.field_corrections = []
        if self.issue_categories is None:
            self.issue_categories = []


class QCInterface:
    """
    Interface for human operators to verify documents.
    
    Features:
    - Fetch tasks from queue
    - Lock tasks during verification
    - Submit corrections and feedback
    - Track operator metrics
    """
    
    def __init__(
        self,
        queue: Optional[QCQueue] = None,
        feedback_collector: Optional[FeedbackCollector] = None
    ):
        """
        Initialize QC interface.
        
        Args:
            queue: QC queue instance
            feedback_collector: Feedback collector instance
        """
        self.queue = queue or QCQueue()
        self.feedback = feedback_collector or FeedbackCollector()
    
    def get_next_task(self, operator_id: str) -> Optional[QCTask]:
        """
        Get next available task for operator.
        
        Prioritizes:
        1. Tasks already assigned to operator
        2. High priority unassigned tasks
        3. Medium priority unassigned tasks
        
        Args:
            operator_id: Operator identifier
            
        Returns:
            Next task or None if queue empty
        """
        # First, check for tasks already assigned to operator
        assigned = self.queue.get_pending_tasks(operator_id=operator_id, limit=1)
        if assigned:
            task = assigned[0]
            if task.acquire_lock(operator_id):
                task.status = TaskStatus.IN_PROGRESS
                self.queue._save_task(task)
                return task
        
        # Get unassigned high-priority tasks
        pending = self.queue.get_pending_tasks(limit=10)
        for task in pending:
            if task.assigned_to is None and task.acquire_lock(operator_id):
                self.queue.assign_task(task.task_id, operator_id)
                task.status = TaskStatus.IN_PROGRESS
                self.queue._save_task(task)
                return task
        
        return None
    
    def get_task_details(self, task_id: str, operator_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full task details for verification.
        
        Args:
            task_id: Task identifier
            operator_id: Operator identifier
            
        Returns:
            Task details dictionary or None
        """
        task = self.queue.get_task(task_id)
        if not task:
            return None
        
        # Check authorization
        if task.assigned_to and task.assigned_to != operator_id:
            return None
        
        return {
            'task_id': task.task_id,
            'page_id': task.page_id,
            'batch_id': task.batch_id,
            'doc_type': task.doc_type,
            'severity': task.severity,
            'priority': task.priority.name,
            'created_at': datetime.fromtimestamp(task.created_at).isoformat(),
            'metadata': task.metadata,
            'image_path': task.image_path,
            'ocr_text': task.ocr_text,
            'extracted_fields': task.extracted_fields,
            'routing_reasons': task.metadata.get('reasons', []),
            'classification_confidence': task.metadata.get('classification_confidence', 0),
            'avg_field_confidence': task.metadata.get('avg_field_confidence', 0),
            'field_confidences': task.metadata.get('field_confidences', {}),
        }
    
    def submit_verification(
        self,
        task_id: str,
        operator_id: str,
        result: VerificationResult
    ) -> bool:
        """
        Submit verification result.
        
        Args:
            task_id: Task identifier
            operator_id: Operator identifier
            result: Verification result
            
        Returns:
            True if submission successful
        """
        task = self.queue.get_task(task_id)
        if not task:
            return False
        
        # Verify operator authorization
        if not task.release_lock(operator_id):
            return False
        
        # Update task based on result
        if result.escalate:
            task.status = TaskStatus.ESCALATED
            task.priority = TaskPriority.CRITICAL
        elif result.approved:
            task.status = TaskStatus.COMPLETED
            # Apply corrections to extracted fields
            if result.field_corrections:
                for correction in result.field_corrections:
                    task.extracted_fields[correction.field_name] = correction.corrected_value
            if result.corrected_doc_type:
                task.doc_type = result.corrected_doc_type
        else:
            task.status = TaskStatus.REJECTED
        
        task.operator_notes = result.notes
        task.completed_at = datetime.now().timestamp()
        
        # Update artifact metadata with QC pass/fail status
        self._update_artifact_metadata(task, result)
        
        # Save updated task
        self.queue._save_task(task)
        
        # Collect feedback for ML training
        field_corrections_list = result.field_corrections or []
        issue_categories_list = result.issue_categories or []
        
        feedback_entry = FeedbackEntry(
            timestamp=datetime.now().timestamp(),
            task_id=task_id,
            page_id=task.page_id,
            batch_id=task.batch_id,
            operator_id=operator_id,
            original_doc_type=task.metadata.get('original_doc_type', task.doc_type),
            corrected_doc_type=result.corrected_doc_type or task.doc_type,
            original_fields=task.metadata.get('original_fields', task.extracted_fields),
            corrected_fields={
                correction.field_name: correction.corrected_value
                for correction in field_corrections_list
            },
            field_corrections=[
                {
                    'field': c.field_name,
                    'original': c.original_value,
                    'corrected': c.corrected_value,
                    'confidence': c.confidence_rating,
                    'notes': c.notes
                }
                for c in field_corrections_list
            ],
            issue_categories=issue_categories_list,
            operator_confidence=result.operator_confidence,
            classification_confidence=task.metadata.get('classification_confidence', 0),
            avg_field_confidence=task.metadata.get('avg_field_confidence', 0),
            severity=task.severity,
            time_spent_seconds=result.time_spent_seconds,
            notes=result.notes,
            approved=result.approved,
            escalated=result.escalate
        )
        
        self.feedback.add_entry(feedback_entry)
        
        return True
    
    def release_task(self, task_id: str, operator_id: str) -> bool:
        """
        Release task lock without completing.
        
        Args:
            task_id: Task identifier
            operator_id: Operator identifier
            
        Returns:
            True if released successfully
        """
        task = self.queue.get_task(task_id)
        if not task:
            return False
        
        if task.release_lock(operator_id):
            if task.status == TaskStatus.IN_PROGRESS:
                task.status = TaskStatus.ASSIGNED
                self.queue._save_task(task)
            return True
        return False
    
    def get_operator_stats(self, operator_id: str) -> Dict[str, Any]:
        """
        Get operator performance statistics.
        
        Args:
            operator_id: Operator identifier
            
        Returns:
            Statistics dictionary
        """
        workload = self.queue.get_operator_workload(operator_id)
        feedback_stats = self.feedback.get_operator_stats(operator_id)
        
        return {
            'operator_id': operator_id,
            'workload': workload,
            'completed_total': feedback_stats.get('total_verifications', 0),
            'approved_count': feedback_stats.get('approved_count', 0),
            'rejected_count': feedback_stats.get('rejected_count', 0),
            'escalated_count': feedback_stats.get('escalated_count', 0),
            'avg_time_per_task': feedback_stats.get('avg_time_seconds', 0),
            'corrections_made': feedback_stats.get('total_corrections', 0),
            'avg_confidence': feedback_stats.get('avg_confidence', 0),
        }
    
    def bulk_assign_tasks(
        self,
        operator_id: str,
        count: int = 10,
        severity: Optional[str] = None,
        doc_type: Optional[str] = None
    ) -> List[str]:
        """
        Bulk assign tasks to operator.
        
        Args:
            operator_id: Operator identifier
            count: Number of tasks to assign
            severity: Filter by severity
            doc_type: Filter by document type
            
        Returns:
            List of assigned task IDs
        """
        pending = self.queue.get_pending_tasks(
            severity=severity,
            doc_type=doc_type,
            limit=count
        )
        
        assigned = []
        for task in pending:
            if task.assigned_to is None:
                if self.queue.assign_task(task.task_id, operator_id):
                    assigned.append(task.task_id)
        
        return assigned
    
    def _update_artifact_metadata(self, task: QCTask, result: VerificationResult) -> None:
        """
        Update document artifact metadata with QC pass/fail status.
        
        Writes QC verification results to:
        1. Metadata JSON file alongside image
        2. Task metadata for persistence
        
        Args:
            task: QC task
            result: Verification result
        """
        import json
        from pathlib import Path
        
        qc_status = {
            'passed': result.approved,
            'verified_at': datetime.now().isoformat(),
            'verified_by': result.operator_id,
            'task_id': task.task_id,
            'time_spent_seconds': result.time_spent_seconds,
            'operator_confidence': result.operator_confidence,
            'corrections_made': len(result.field_corrections) if result.field_corrections else 0,
            'escalated': result.escalate,
            'notes': result.notes,
            'corrected_doc_type': result.corrected_doc_type,
            'issue_categories': [cat.value for cat in (result.issue_categories or [])]
        }
        
        # Update task metadata
        task.metadata['qc_status'] = qc_status
        
        # Write to metadata JSON file if image path exists
        if task.image_path:
            try:
                image_path = Path(task.image_path)
                metadata_path = image_path.with_suffix('.json')
                
                metadata = {}
                if metadata_path.exists():
                    try:
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                    except:
                        pass
                
                # Add/update QC status in metadata
                if 'processing' not in metadata:
                    metadata['processing'] = {}
                metadata['processing']['qc_verification'] = qc_status
                
                # Write back
                metadata_path.parent.mkdir(parents=True, exist_ok=True)
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
            
            except Exception as e:
                print(f"Warning: Failed to write QC metadata to file: {e}")
        
        # Also write to separate QC results log for easy access
        try:
            qc_results_dir = Path("data/qc_results")
            qc_results_dir.mkdir(parents=True, exist_ok=True)
            
            result_file = qc_results_dir / f"{task.page_id}_qc.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'page_id': task.page_id,
                    'task_id': task.task_id,
                    'doc_type': result.corrected_doc_type or task.doc_type,
                    'qc_status': qc_status,
                    'original_fields': task.metadata.get('original_fields', {}),
                    'corrected_fields': task.extracted_fields,
                    'field_corrections': [
                        {
                            'field': c.field_name,
                            'original': c.original_value,
                            'corrected': c.corrected_value,
                            'confidence': c.confidence_rating
                        }
                        for c in (result.field_corrections or [])
                    ]
                }, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to write QC result file: {e}")
