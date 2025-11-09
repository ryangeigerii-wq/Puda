"""
QC Queue Management

Handles task queue for documents requiring human verification.
Supports task assignment, locking, status tracking, and priority queuing.
"""

import json
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any
from threading import Lock


class TaskStatus(Enum):
    """Status of a QC task."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class TaskPriority(Enum):
    """Priority level for QC tasks."""
    LOW = 1          # auto-routed with minor issues
    MEDIUM = 2       # qc_queue tier
    HIGH = 3         # manual_review tier
    CRITICAL = 4     # escalated or time-sensitive


@dataclass
class QCTask:
    """
    Represents a document requiring QC verification.
    
    Attributes:
        task_id: Unique identifier
        page_id: Document page identifier
        batch_id: Batch identifier
        doc_type: Classified document type
        severity: Routing severity (qc_queue, manual_review)
        status: Current task status
        priority: Task priority level
        created_at: Task creation timestamp
        assigned_to: Operator ID (if assigned)
        assigned_at: Assignment timestamp
        completed_at: Completion timestamp
        locked_by: Operator currently holding lock
        locked_at: Lock acquisition timestamp
        metadata: Additional document metadata (confidences, reasons, etc.)
        image_path: Path to document image
        ocr_text: Extracted OCR text
        extracted_fields: Current field extractions
        operator_notes: Notes from operator
    """
    task_id: str
    page_id: str
    batch_id: str
    doc_type: str
    severity: str
    status: TaskStatus
    priority: TaskPriority
    created_at: float
    assigned_to: Optional[str] = None
    assigned_at: Optional[float] = None
    completed_at: Optional[float] = None
    locked_by: Optional[str] = None
    locked_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    image_path: Optional[str] = None
    ocr_text: Optional[str] = None
    extracted_fields: Dict[str, Any] = field(default_factory=dict)
    operator_notes: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert task to dictionary for serialization."""
        data = asdict(self)
        data['status'] = self.status.value
        data['priority'] = self.priority.value
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'QCTask':
        """Create task from dictionary."""
        data['status'] = TaskStatus(data['status'])
        data['priority'] = TaskPriority(data['priority'])
        return cls(**data)
    
    def is_locked(self) -> bool:
        """Check if task is currently locked."""
        if not self.locked_by:
            return False
        # Auto-release locks after 30 minutes
        if time.time() - (self.locked_at or 0) > 1800:
            return False
        return True
    
    def acquire_lock(self, operator_id: str) -> bool:
        """Attempt to acquire task lock."""
        if self.is_locked() and self.locked_by != operator_id:
            return False
        self.locked_by = operator_id
        self.locked_at = time.time()
        return True
    
    def release_lock(self, operator_id: str) -> bool:
        """Release task lock."""
        if self.locked_by != operator_id:
            return False
        self.locked_by = None
        self.locked_at = None
        return True


class QCQueue:
    """
    Manages queue of documents requiring human verification.
    
    Features:
    - Priority-based task queuing
    - Task assignment and locking
    - Status tracking and persistence
    - Operator workload management
    """
    
    def __init__(self, queue_file: str = "data/qc_queue.jsonl"):
        """
        Initialize QC queue.
        
        Args:
            queue_file: Path to queue persistence file
        """
        self.queue_file = Path(queue_file)
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self.tasks: Dict[str, QCTask] = {}
        self._load_queue()
    
    def _load_queue(self):
        """Load queue from persistence file."""
        if not self.queue_file.exists():
            return
        
        with open(self.queue_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        task = QCTask.from_dict(data)
                        self.tasks[task.task_id] = task
                    except Exception as e:
                        print(f"Warning: Failed to load task: {e}")
    
    def _save_task(self, task: QCTask):
        """Append task to persistence file."""
        try:
            with open(self.queue_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(task.to_dict()) + '\n')
        except Exception as e:
            print(f"Warning: Failed to save task: {e}")
    
    def add_task(self, task: QCTask) -> bool:
        """
        Add task to queue.
        
        Args:
            task: QC task to add
            
        Returns:
            True if added successfully
        """
        with self._lock:
            if task.task_id in self.tasks:
                return False
            self.tasks[task.task_id] = task
            self._save_task(task)
            return True
    
    def get_task(self, task_id: str) -> Optional[QCTask]:
        """Get task by ID."""
        return self.tasks.get(task_id)
    
    def get_pending_tasks(
        self,
        operator_id: Optional[str] = None,
        severity: Optional[str] = None,
        doc_type: Optional[str] = None,
        limit: int = 50
    ) -> List[QCTask]:
        """
        Get pending tasks with optional filters.
        
        Args:
            operator_id: Filter by assigned operator
            severity: Filter by severity level
            doc_type: Filter by document type
            limit: Maximum tasks to return
            
        Returns:
            List of matching tasks, sorted by priority (high to low)
        """
        tasks = []
        for task in self.tasks.values():
            # Filter by status
            if task.status not in [TaskStatus.PENDING, TaskStatus.ASSIGNED]:
                continue
            
            # Filter by operator
            if operator_id and task.assigned_to != operator_id:
                continue
            
            # Filter by severity
            if severity and task.severity != severity:
                continue
            
            # Filter by doc type
            if doc_type and task.doc_type != doc_type:
                continue
            
            tasks.append(task)
        
        # Sort by priority (high to low), then by creation time (oldest first)
        tasks.sort(key=lambda t: (-t.priority.value, t.created_at))
        return tasks[:limit]
    
    def assign_task(self, task_id: str, operator_id: str) -> bool:
        """
        Assign task to operator.
        
        Args:
            task_id: Task identifier
            operator_id: Operator identifier
            
        Returns:
            True if assigned successfully
        """
        with self._lock:
            task = self.tasks.get(task_id)
            if not task or task.status not in [TaskStatus.PENDING, TaskStatus.ASSIGNED]:
                return False
            
            task.assigned_to = operator_id
            task.assigned_at = time.time()
            task.status = TaskStatus.ASSIGNED
            self._save_task(task)
            return True
    
    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        operator_id: str
    ) -> bool:
        """
        Update task status.
        
        Args:
            task_id: Task identifier
            status: New status
            operator_id: Operator making the update
            
        Returns:
            True if updated successfully
        """
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            
            # Verify operator authorization
            if task.assigned_to and task.assigned_to != operator_id:
                return False
            
            task.status = status
            if status == TaskStatus.COMPLETED:
                task.completed_at = time.time()
            
            self._save_task(task)
            return True
    
    def get_operator_workload(self, operator_id: str) -> Dict[str, int]:
        """
        Get operator workload statistics.
        
        Args:
            operator_id: Operator identifier
            
        Returns:
            Dictionary with counts by status
        """
        workload = {
            'assigned': 0,
            'in_progress': 0,
            'completed_today': 0
        }
        
        today_start = datetime.now().replace(hour=0, minute=0, second=0).timestamp()
        
        for task in self.tasks.values():
            if task.assigned_to != operator_id:
                continue
            
            if task.status == TaskStatus.ASSIGNED:
                workload['assigned'] += 1
            elif task.status == TaskStatus.IN_PROGRESS:
                workload['in_progress'] += 1
            elif task.status == TaskStatus.COMPLETED and (task.completed_at or 0) >= today_start:
                workload['completed_today'] += 1
        
        return workload
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get overall queue statistics.
        
        Returns:
            Dictionary with queue metrics
        """
        stats = {
            'total': len(self.tasks),
            'pending': 0,
            'assigned': 0,
            'in_progress': 0,
            'completed': 0,
            'by_severity': {},
            'by_doc_type': {},
            'by_priority': {}
        }
        
        for task in self.tasks.values():
            # Count by status
            if task.status == TaskStatus.PENDING:
                stats['pending'] += 1
            elif task.status == TaskStatus.ASSIGNED:
                stats['assigned'] += 1
            elif task.status == TaskStatus.IN_PROGRESS:
                stats['in_progress'] += 1
            elif task.status == TaskStatus.COMPLETED:
                stats['completed'] += 1
            
            # Count by severity
            stats['by_severity'][task.severity] = stats['by_severity'].get(task.severity, 0) + 1
            
            # Count by doc type
            stats['by_doc_type'][task.doc_type] = stats['by_doc_type'].get(task.doc_type, 0) + 1
            
            # Count by priority
            priority_name = task.priority.name
            stats['by_priority'][priority_name] = stats['by_priority'].get(priority_name, 0) + 1
        
        return stats
