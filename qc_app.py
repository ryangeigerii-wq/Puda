"""
QC Web Application API

Serves QC interface with image display, text overlay, and correction capabilities.
"""

from flask import Flask, jsonify, request, send_file, send_from_directory
from pathlib import Path
from typing import Optional
import json
import base64
from io import BytesIO

from src.qc.queue import QCQueue, TaskStatus
from src.qc.interface import QCInterface, VerificationResult, FieldCorrection
from src.qc.feedback import FeedbackCollector, IssueCategory

app = Flask(__name__, static_folder='static/qc')

# Global instances
qc_interface: Optional[QCInterface] = None


@app.route('/')
def index():
    """Serve QC interface."""
    return send_from_directory('static/qc', 'qc_interface.html')


@app.route('/api/qc/task/next')
def get_next_task():
    """Get next task for operator."""
    operator_id = request.args.get('operator_id', 'default_operator')
    
    if not qc_interface:
        return jsonify({"error": "QC not initialized"}), 503
    
    task = qc_interface.get_next_task(operator_id)
    if not task:
        return jsonify({"status": "empty", "message": "No tasks available"})
    
    task_details = qc_interface.get_task_details(task.task_id, operator_id)
    
    return jsonify({
        "status": "ok",
        "task": task_details
    })


@app.route('/api/qc/task/<task_id>')
def get_task_details_endpoint(task_id: str):
    """Get detailed task information."""
    operator_id = request.args.get('operator_id', 'default_operator')
    
    if not qc_interface:
        return jsonify({"error": "QC not initialized"}), 503
    
    task_details = qc_interface.get_task_details(task_id, operator_id)
    if not task_details:
        return jsonify({"error": "Task not found"}), 404
    
    return jsonify({
        "status": "ok",
        "task": task_details
    })


@app.route('/api/qc/image/<path:image_path>')
def serve_image(image_path: str):
    """Serve document image."""
    try:
        # Resolve relative to project root
        full_path = Path(image_path)
        if not full_path.exists():
            # Try relative to data directory
            full_path = Path('data') / image_path
        
        if not full_path.exists():
            return jsonify({"error": "Image not found"}), 404
        
        return send_file(full_path, mimetype='image/png')
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/qc/task/<task_id>/submit', methods=['POST'])
def submit_verification_endpoint(task_id: str):
    """Submit verification result."""
    try:
        data = request.json
        operator_id = data.get('operator_id', 'default_operator')
        
        # Build field corrections
        field_corrections = []
        for corr in data.get('field_corrections', []):
            field_corrections.append(FieldCorrection(
                field_name=corr['field_name'],
                original_value=corr['original_value'],
                corrected_value=corr['corrected_value'],
                confidence_rating=corr.get('confidence_rating', 1.0),
                notes=corr.get('notes')
            ))
        
        # Parse issue categories
        issue_categories = [
            IssueCategory(cat) for cat in data.get('issue_categories', [])
        ]
        
        # Build verification result
        result = VerificationResult(
            task_id=task_id,
            operator_id=operator_id,
            approved=data.get('approved', False),
            corrected_doc_type=data.get('corrected_doc_type'),
            field_corrections=field_corrections,
            issue_categories=issue_categories,
            operator_confidence=data.get('operator_confidence', 1.0),
            time_spent_seconds=data.get('time_spent_seconds', 0),
            notes=data.get('notes'),
            escalate=data.get('escalate', False)
        )
        
        # Submit verification
        success = qc_interface.submit_verification(task_id, operator_id, result)
        
        if success:
            # Update document metadata with pass/fail
            _update_document_metadata(task_id, result.approved)
            
            return jsonify({
                "status": "ok",
                "message": "Verification submitted successfully"
            })
        else:
            return jsonify({"error": "Failed to submit verification"}), 400
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/qc/task/<task_id>/release', methods=['POST'])
def release_task_endpoint(task_id: str):
    """Release task without completing."""
    try:
        data = request.json
        operator_id = data.get('operator_id', 'default_operator')
        
        success = qc_interface.release_task(task_id, operator_id)
        
        if success:
            return jsonify({
                "status": "ok",
                "message": "Task released"
            })
        else:
            return jsonify({"error": "Failed to release task"}), 400
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/qc/operator/<operator_id>/stats')
def get_operator_stats_endpoint(operator_id: str):
    """Get operator statistics."""
    if not qc_interface:
        return jsonify({"error": "QC not initialized"}), 503
    
    stats = qc_interface.get_operator_stats(operator_id)
    
    return jsonify({
        "status": "ok",
        "stats": stats
    })


@app.route('/api/qc/issue_categories')
def get_issue_categories():
    """Get available issue categories."""
    categories = [
        {"value": cat.value, "label": cat.value.replace('_', ' ').title()}
        for cat in IssueCategory
    ]
    return jsonify({
        "status": "ok",
        "categories": categories
    })


def _update_document_metadata(task_id: str, passed: bool):
    """Update document metadata with QC pass/fail status."""
    try:
        task = qc_interface.queue.get_task(task_id)
        if not task:
            return
        
        # Update metadata file if it exists
        # Assume metadata stored alongside image as .json
        if task.image_path:
            image_path = Path(task.image_path)
            metadata_path = image_path.with_suffix('.json')
            
            metadata = {}
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            
            # Add QC status
            metadata['qc_status'] = {
                'passed': passed,
                'verified_at': task.completed_at,
                'verified_by': task.assigned_to,
                'task_id': task_id
            }
            
            # Write updated metadata
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
    
    except Exception as e:
        print(f"Warning: Failed to update document metadata: {e}")


def init_qc_interface():
    """Initialize QC interface."""
    global qc_interface
    qc_interface = QCInterface()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description="QC Web Application")
    parser.add_argument('--port', '-p', type=int, default=8081, help='Server port')
    parser.add_argument('--host', default='127.0.0.1', help='Server host')
    parser.add_argument('--debug', action='store_true', help='Debug mode')
    args = parser.parse_args()
    
    init_qc_interface()
    
    print(f"Starting QC Web Application on {args.host}:{args.port}")
    print(f"QC Interface: http://{args.host}:{args.port}/")
    
    app.run(host=args.host, port=args.port, debug=args.debug)
