#!/usr/bin/env python3
"""
QC Verification CLI

Interactive command-line interface for operators to verify documents.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from datetime import datetime

from src.qc.queue import QCQueue, TaskStatus
from src.qc.interface import QCInterface, VerificationResult, FieldCorrection
from src.qc.feedback import IssueCategory


def print_header(title: str):
    """Print formatted header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def print_task_details(task_details: dict):
    """Print formatted task details."""
    print(f"Task ID: {task_details['task_id']}")
    print(f"Page ID: {task_details['page_id']}")
    print(f"Batch ID: {task_details['batch_id']}")
    print(f"Document Type: {task_details['doc_type']}")
    print(f"Severity: {task_details['severity']}")
    print(f"Priority: {task_details['priority']}")
    print(f"Created: {task_details['created_at']}")
    print(f"\nClassification Confidence: {task_details['classification_confidence']:.2f}")
    print(f"Average Field Confidence: {task_details['avg_field_confidence']:.2f}")
    
    if task_details['routing_reasons']:
        print(f"\nRouting Reasons:")
        for reason in task_details['routing_reasons']:
            print(f"  - {reason}")
    
    print(f"\n--- Extracted Fields ---")
    for field, value in task_details['extracted_fields'].items():
        confidence = task_details['field_confidences'].get(field, 'N/A')
        print(f"  {field}: {value} (confidence: {confidence})")
    
    if task_details.get('image_path'):
        print(f"\nImage Path: {task_details['image_path']}")
    
    if task_details.get('ocr_text'):
        print(f"\nOCR Text (first 200 chars):")
        print(f"  {task_details['ocr_text'][:200]}...")


def get_next_task(interface: QCInterface, operator_id: str):
    """Get and display next task."""
    print_header("Fetching Next Task")
    
    task = interface.get_next_task(operator_id)
    if not task:
        print("No tasks available in queue.")
        return None
    
    task_details = interface.get_task_details(task.task_id, operator_id)
    if not task_details:
        print("Error: Could not load task details.")
        return None
    
    print_task_details(task_details)
    return task


def verify_task(interface: QCInterface, task, operator_id: str):
    """Interactive verification of task."""
    start_time = time.time()
    
    print_header("Verification")
    
    # Ask for approval
    while True:
        action = input("\nAction [a]pprove / [r]eject / [e]scalate / [s]kip: ").lower()
        if action in ['a', 'r', 'e', 's']:
            break
        print("Invalid choice. Please enter a, r, e, or s.")
    
    if action == 's':
        interface.release_task(task.task_id, operator_id)
        print("Task released back to queue.")
        return
    
    # Initialize result
    result = VerificationResult(
        task_id=task.task_id,
        operator_id=operator_id,
        approved=(action == 'a'),
        escalate=(action == 'e'),
        field_corrections=[],
        issue_categories=[]
    )
    
    # Collect field corrections if needed
    if action in ['a', 'r']:
        print("\n--- Field Corrections ---")
        print("Enter field corrections (leave blank to skip)")
        
        for field, value in task.extracted_fields.items():
            correction = input(f"{field} [{value}]: ").strip()
            if correction and correction != str(value):
                confidence = input(f"  Confidence in correction (0-1) [1.0]: ").strip()
                confidence = float(confidence) if confidence else 1.0
                notes = input(f"  Notes (optional): ").strip() or None
                
                result.field_corrections.append(FieldCorrection(
                    field_name=field,
                    original_value=value,
                    corrected_value=correction,
                    confidence_rating=confidence,
                    notes=notes
                ))
        
        # Check if document type needs correction
        corrected_type = input(f"\nCorrected doc type [{task.doc_type}]: ").strip()
        if corrected_type and corrected_type != task.doc_type:
            result.corrected_doc_type = corrected_type
    
    # Collect issue categories
    if action in ['r', 'e']:
        print("\n--- Issue Categories ---")
        print("Select issue categories (comma-separated numbers):")
        categories = list(IssueCategory)
        for i, cat in enumerate(categories, 1):
            print(f"  {i}. {cat.value}")
        
        selected = input("\nCategories: ").strip()
        if selected:
            indices = [int(x.strip()) - 1 for x in selected.split(',') if x.strip().isdigit()]
            result.issue_categories = [categories[i] for i in indices if 0 <= i < len(categories)]
    
    # Operator confidence
    confidence = input("\nYour confidence in this verification (0-1) [1.0]: ").strip()
    result.operator_confidence = float(confidence) if confidence else 1.0
    
    # Notes
    notes = input("Additional notes (optional): ").strip()
    result.notes = notes or None
    
    # Calculate time spent
    result.time_spent_seconds = int(time.time() - start_time)
    
    # Submit verification
    if interface.submit_verification(task.task_id, operator_id, result):
        corrections_count = len(result.field_corrections) if result.field_corrections else 0
        print(f"\n✓ Verification submitted successfully!")
        print(f"  Time spent: {result.time_spent_seconds}s")
        print(f"  Corrections made: {corrections_count}")
    else:
        print("\n✗ Error submitting verification")


def show_stats(interface: QCInterface, operator_id: str):
    """Show operator statistics."""
    print_header("Your Statistics")
    
    stats = interface.get_operator_stats(operator_id)
    
    print(f"Operator: {stats['operator_id']}")
    print(f"\nWorkload:")
    print(f"  Assigned: {stats['workload']['assigned']}")
    print(f"  In Progress: {stats['workload']['in_progress']}")
    print(f"  Completed Today: {stats['workload']['completed_today']}")
    
    print(f"\nPerformance:")
    print(f"  Total Completed: {stats['completed_total']}")
    print(f"  Approved: {stats['approved_count']}")
    print(f"  Rejected: {stats['rejected_count']}")
    print(f"  Escalated: {stats['escalated_count']}")
    print(f"  Corrections Made: {stats['corrections_made']}")
    print(f"  Avg Time per Task: {stats['avg_time_per_task']:.1f}s")
    print(f"  Avg Confidence: {stats['avg_confidence']:.2f}")


def show_queue_stats(queue: QCQueue):
    """Show queue statistics."""
    print_header("Queue Statistics")
    
    stats = queue.get_queue_stats()
    
    print(f"Total Tasks: {stats['total']}")
    print(f"  Pending: {stats['pending']}")
    print(f"  Assigned: {stats['assigned']}")
    print(f"  In Progress: {stats['in_progress']}")
    print(f"  Completed: {stats['completed']}")
    
    print(f"\nBy Severity:")
    for severity, count in stats['by_severity'].items():
        print(f"  {severity}: {count}")
    
    print(f"\nBy Document Type:")
    for doc_type, count in stats['by_doc_type'].items():
        print(f"  {doc_type}: {count}")
    
    print(f"\nBy Priority:")
    for priority, count in stats['by_priority'].items():
        print(f"  {priority}: {count}")


def interactive_mode(operator_id: str):
    """Run interactive verification session."""
    interface = QCInterface()
    
    print_header("QC Verification Interface")
    print(f"Operator: {operator_id}")
    print("Type 'help' for commands")
    
    current_task = None
    
    while True:
        if not current_task:
            command = input("\n> ").strip().lower()
        else:
            command = "verify"
        
        if command in ['quit', 'exit', 'q']:
            if current_task:
                interface.release_task(current_task.task_id, operator_id)
            print("Goodbye!")
            break
        
        elif command in ['next', 'n', '']:
            current_task = get_next_task(interface, operator_id)
        
        elif command == 'verify' and current_task:
            verify_task(interface, current_task, operator_id)
            current_task = None
        
        elif command in ['stats', 'mystats']:
            show_stats(interface, operator_id)
        
        elif command in ['queue', 'qstats']:
            show_queue_stats(interface.queue)
        
        elif command == 'help':
            print("\nCommands:")
            print("  next, n       - Get next task")
            print("  stats         - Show your statistics")
            print("  queue         - Show queue statistics")
            print("  help          - Show this help")
            print("  quit, q       - Exit")
        
        else:
            print(f"Unknown command: {command}. Type 'help' for commands.")


def main():
    parser = argparse.ArgumentParser(
        description="QC Verification CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive verification session
  python qc_verify_cli.py --operator alice

  # Show queue statistics
  python qc_verify_cli.py --queue-stats

  # Show operator statistics
  python qc_verify_cli.py --operator alice --stats
        """
    )
    
    parser.add_argument(
        '--operator',
        help='Operator ID'
    )
    parser.add_argument(
        '--queue-stats',
        action='store_true',
        help='Show queue statistics'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show operator statistics'
    )
    
    args = parser.parse_args()
    
    if args.queue_stats:
        queue = QCQueue()
        show_queue_stats(queue)
        return
    
    if not args.operator:
        print("Error: --operator required")
        parser.print_help()
        return 1
    
    if args.stats:
        interface = QCInterface()
        show_stats(interface, args.operator)
        return
    
    # Start interactive mode
    interactive_mode(args.operator)


if __name__ == '__main__':
    sys.exit(main() or 0)
