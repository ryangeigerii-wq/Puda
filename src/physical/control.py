"""
Paper Movement Control System
Purpose: Move and control paper safely through zones
"""
from typing import Dict, List, Optional
from datetime import datetime
import logging

from .zones import IntakeZone, PrepZone, ScanningZone, QCZone, OutputRack, Box, Paper, ZoneType, PaperStatus, ScannerType, OutputDisposition


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PaperControlSystem:
    """
    Central control system for managing paper movement
    Ensures safe handling and tracking of physical documents
    
    UNIDIRECTIONAL FLOW (Left to Right):
    ➊ Intake → ➋ Prep → ➌ Scanning → ➍ QC → ➎ Output
    
    No backwards movement except: QC → Scanning (rescan only)
    """
    
    def __init__(self):
        self.intake_zone = IntakeZone()
        self.prep_zone = PrepZone()
        self.scanning_zone = ScanningZone()
        self.qc_zone = QCZone()
        self.output_rack = OutputRack()
        self.movement_log: List[Dict] = []
    
    def get_workflow_status(self) -> Dict:
        """
        Get visual representation of the entire workflow
        Shows left-to-right flow with current status of each zone
        """
        intake_status = self.intake_zone.get_status()
        prep_status = self.prep_zone.get_status()
        scan_status = self.scanning_zone.get_status()
        qc_status = self.qc_zone.get_status()
        output_status = self.output_rack.get_status()
        
        return {
            'flow': '➊ Intake → ➋ Prep → ➌ Scanning → ➍ QC → ➎ Output',
            'zones': [
                {
                    'order': 1,
                    'name': 'Intake',
                    'icon': '📥',
                    'boxes': intake_status['boxes_received'],
                    'capacity': f"{intake_status['boxes_received']}/{intake_status['capacity']}",
                    'status': 'active' if intake_status['boxes_received'] > 0 else 'empty'
                },
                {
                    'order': 2,
                    'name': 'Prep',
                    'icon': '🔧',
                    'papers': prep_status['total_papers'],
                    'capacity': f"{prep_status['total_papers']}/unlimited",
                    'status': 'active' if prep_status['total_papers'] > 0 else 'empty'
                },
                {
                    'order': 3,
                    'name': 'Scanning',
                    'icon': '📸',
                    'papers': scan_status['queue_length'],
                    'capacity': f"{scan_status['queue_length']}/{scan_status['capacity']}",
                    'status': 'active' if scan_status['queue_length'] > 0 else 'empty'
                },
                {
                    'order': 4,
                    'name': 'QC',
                    'icon': '✅',
                    'papers': qc_status['total_papers'],
                    'capacity': f"{qc_status['total_papers']}/{qc_status['capacity']}",
                    'status': 'active' if qc_status['total_papers'] > 0 else 'empty'
                },
                {
                    'order': 5,
                    'name': 'Output',
                    'icon': '📤',
                    'papers': output_status['total_papers'],
                    'capacity': f"{output_status['total_papers']}/{output_status['capacity']}",
                    'status': 'active' if output_status['total_papers'] > 0 else 'empty'
                }
            ],
            'total_papers_in_system': (
                prep_status['total_papers'] +
                scan_status['queue_length'] +
                qc_status['total_papers'] +
                output_status['total_papers']
            ),
            'completed_papers': output_status['completed_papers']
        }
    
    def validate_movement(self, from_zone: ZoneType, to_zone: ZoneType) -> Dict:
        """
        Validate if movement between zones is allowed (enforces left-to-right flow)
        
        Args:
            from_zone: Source zone
            to_zone: Destination zone
            
        Returns:
            Validation result with allowed status and reason
        """
        if from_zone.can_move_to(to_zone):
            return {
                'allowed': True,
                'reason': f'Valid forward movement: {from_zone.get_icon()} {from_zone.value} → {to_zone.get_icon()} {to_zone.value}'
            }
        
        # Check if it's a rescan scenario
        if from_zone == ZoneType.QC and to_zone == ZoneType.SCANNING:
            return {
                'allowed': True,
                'reason': 'QC rescan: Failed papers returning to scanning'
            }
        
        return {
            'allowed': False,
            'reason': f'❌ BLOCKED: Cannot move backwards from {from_zone.value} to {to_zone.value}. Flow is unidirectional: Intake → Prep → Scanning → QC → Output'
        }
    
    def receive_box(self, box_id: str) -> Dict:
        """
        Receive a box in the intake zone
        
        Args:
            box_id: Unique identifier for the box
            
        Returns:
            Receipt confirmation with box details
        """
        try:
            box = self.intake_zone.receive_box(box_id)
            
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': 'RECEIVE',
                'box_id': box_id,
                'zone': ZoneType.INTAKE.value,
                'status': 'success'
            }
            self.movement_log.append(log_entry)
            
            logger.info(f"Box {box_id} received in intake zone")
            
            return {
                'success': True,
                'box_id': box.box_id,
                'received_at': box.received_at.isoformat(),
                'status': box.status.value,
                'next_step': 'Log box details (paper count and notes)'
            }
            
        except Exception as e:
            logger.error(f"Failed to receive box {box_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def log_box_details(self, box_id: str, paper_count: int, notes: str = "") -> Dict:
        """
        Log the details of a received box
        
        Args:
            box_id: Box identifier
            paper_count: Number of papers in the box
            notes: Additional information
            
        Returns:
            Logging confirmation
        """
        try:
            box = self.intake_zone.log_box(box_id, paper_count, notes)
            
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': 'LOG',
                'box_id': box_id,
                'paper_count': paper_count,
                'status': 'success'
            }
            self.movement_log.append(log_entry)
            
            logger.info(f"Box {box_id} logged with {paper_count} papers")
            
            return {
                'success': True,
                'box_id': box.box_id,
                'paper_count': box.paper_count,
                'status': box.status.value,
                'ready_for_processing': True
            }
            
        except Exception as e:
            logger.error(f"Failed to log box {box_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_intake_status(self) -> Dict:
        """Get current status of the intake zone"""
        status = self.intake_zone.get_status()
        status['logged_boxes'] = [
            {
                'box_id': box.box_id,
                'paper_count': box.paper_count,
                'received_at': box.received_at.isoformat()
            }
            for box in self.intake_zone.get_logged_boxes()
        ]
        return status
    
    def get_box_info(self, box_id: str) -> Optional[Dict]:
        """Get detailed information about a specific box"""
        box = self.intake_zone.get_box(box_id)
        if box is None:
            return None
        
        return {
            'box_id': box.box_id,
            'received_at': box.received_at.isoformat(),
            'status': box.status.value,
            'current_zone': box.current_zone.value,
            'paper_count': box.paper_count,
            'notes': box.notes,
            'metadata': box.metadata
        }
    
    def get_movement_history(self, box_id: Optional[str] = None) -> List[Dict]:
        """
        Get movement history log
        
        Args:
            box_id: Optional filter for specific box
            
        Returns:
            List of movement log entries
        """
        if box_id:
            return [log for log in self.movement_log if log.get('box_id') == box_id]
        return self.movement_log
    
    def move_box_to_prep(self, box_id: str) -> Dict:
        """
        Move a logged box from intake to prep zone
        Enforces unidirectional flow: Intake (➊) → Prep (➋)
        
        Args:
            box_id: Box identifier
            
        Returns:
            Movement confirmation
        """
        try:
            # Validate flow direction
            validation = self.validate_movement(ZoneType.INTAKE, ZoneType.PREP)
            if not validation['allowed']:
                return {'success': False, 'error': validation['reason']}
            
            # Move from intake
            box = self.intake_zone.move_box_to_next_zone(box_id, ZoneType.PREP)
            
            # Receive in prep
            box = self.prep_zone.receive_box(box)
            
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': 'MOVE_TO_PREP',
                'box_id': box_id,
                'from_zone': ZoneType.INTAKE.value,
                'to_zone': ZoneType.PREP.value,
                'flow': '➊ → ➋',
                'status': 'success'
            }
            self.movement_log.append(log_entry)
            
            logger.info(f"Box {box_id} moved to prep zone (➊ → ➋)")
            
            return {
                'success': True,
                'box_id': box.box_id,
                'current_zone': box.current_zone.value,
                'status': box.status.value,
                'flow_direction': '➊ Intake → ➋ Prep',
                'next_step': 'Start unboxing process'
            }
            
        except Exception as e:
            logger.error(f"Failed to move box {box_id} to prep: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def start_unboxing(self, box_id: str) -> Dict:
        """Start unboxing a box in prep zone"""
        try:
            result = self.prep_zone.start_unboxing(box_id)
            
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': 'START_UNBOXING',
                'box_id': box_id,
                'status': 'success'
            }
            self.movement_log.append(log_entry)
            
            logger.info(f"Started unboxing box {box_id}")
            return {'success': True, **result}
            
        except Exception as e:
            logger.error(f"Failed to start unboxing {box_id}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def add_paper(self, box_id: str, paper_id: str, has_staples: bool = True, 
                  pages: int = 1) -> Dict:
        """Add a paper from unboxing"""
        try:
            paper = self.prep_zone.add_paper_from_box(box_id, paper_id, has_staples, pages)
            
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': 'ADD_PAPER',
                'box_id': box_id,
                'paper_id': paper_id,
                'has_staples': has_staples,
                'status': 'success'
            }
            self.movement_log.append(log_entry)
            
            logger.info(f"Added paper {paper_id} from box {box_id}")
            
            return {
                'success': True,
                'paper_id': paper.paper_id,
                'box_id': paper.box_id,
                'has_staples': paper.has_staples,
                'status': paper.status.value
            }
            
        except Exception as e:
            logger.error(f"Failed to add paper {paper_id}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def remove_staples(self, paper_id: str) -> Dict:
        """Remove staples from a paper"""
        try:
            paper = self.prep_zone.remove_staples(paper_id)
            
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': 'REMOVE_STAPLES',
                'paper_id': paper_id,
                'status': 'success'
            }
            self.movement_log.append(log_entry)
            
            logger.info(f"Removed staples from paper {paper_id}")
            
            return {
                'success': True,
                'paper_id': paper.paper_id,
                'has_staples': paper.has_staples,
                'status': paper.status.value
            }
            
        except Exception as e:
            logger.error(f"Failed to remove staples from {paper_id}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def mark_paper_ready(self, paper_id: str) -> Dict:
        """Mark paper as ready for scanning"""
        try:
            paper = self.prep_zone.mark_paper_ready(paper_id)
            
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': 'PAPER_READY',
                'paper_id': paper_id,
                'status': 'success'
            }
            self.movement_log.append(log_entry)
            
            logger.info(f"Paper {paper_id} marked ready for scanning")
            
            return {
                'success': True,
                'paper_id': paper.paper_id,
                'status': paper.status.value,
                'ready_for_scanning': True
            }
            
        except Exception as e:
            logger.error(f"Failed to mark paper {paper_id} ready: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def complete_box_prep(self, box_id: str) -> Dict:
        """Mark entire box prep as complete"""
        try:
            box = self.prep_zone.complete_box_prep(box_id)
            
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': 'COMPLETE_BOX_PREP',
                'box_id': box_id,
                'status': 'success'
            }
            self.movement_log.append(log_entry)
            
            logger.info(f"Completed prep for box {box_id}")
            
            return {
                'success': True,
                'box_id': box.box_id,
                'status': box.status.value,
                'next_step': 'Move to scanning zone'
            }
            
        except Exception as e:
            logger.error(f"Failed to complete prep for box {box_id}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_prep_status(self) -> Dict:
        """Get current status of the prep zone"""
        return self.prep_zone.get_status()
    
    def get_paper_info(self, paper_id: str) -> Optional[Dict]:
        """Get detailed information about a specific paper"""
        paper = self.prep_zone.get_paper(paper_id)
        if paper is None:
            return None
        
        return {
            'paper_id': paper.paper_id,
            'box_id': paper.box_id,
            'status': paper.status.value,
            'current_zone': paper.current_zone.value,
            'has_staples': paper.has_staples,
            'pages': paper.pages,
            'notes': paper.notes,
            'metadata': paper.metadata
        }
    
    def move_papers_to_scanning(self, box_id: str) -> Dict:
        """
        Move all prepared papers from a box to scanning zone
        Enforces unidirectional flow: Prep (➋) → Scanning (➌)
        
        Args:
            box_id: Box identifier
            
        Returns:
            Movement confirmation
        """
        try:
            # Validate flow direction
            validation = self.validate_movement(ZoneType.PREP, ZoneType.SCANNING)
            if not validation['allowed']:
                return {'success': False, 'error': validation['reason']}
            
            # Move from prep
            papers = self.prep_zone.move_papers_to_scanning(box_id)
            
            # Receive in scanning
            self.scanning_zone.receive_papers(papers)
            
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': 'MOVE_TO_SCANNING',
                'box_id': box_id,
                'paper_count': len(papers),
                'from_zone': ZoneType.PREP.value,
                'to_zone': ZoneType.SCANNING.value,
                'flow': '➋ → ➌',
                'status': 'success'
            }
            self.movement_log.append(log_entry)
            
            logger.info(f"Moved {len(papers)} papers from box {box_id} to scanning zone (➋ → ➌)")
            
            return {
                'success': True,
                'box_id': box_id,
                'papers_moved': len(papers),
                'paper_ids': [p.paper_id for p in papers],
                'flow_direction': '➋ Prep → ➌ Scanning',
                'next_step': 'Start scanning papers'
            }
            
        except Exception as e:
            logger.error(f"Failed to move papers to scanning: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def start_scan(self, paper_id: str, station_id: Optional[str] = None) -> Dict:
        """Start scanning a paper"""
        try:
            result = self.scanning_zone.start_scan(paper_id, station_id)
            
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': 'START_SCAN',
                'paper_id': paper_id,
                'station_id': result['station_id'],
                'status': 'success'
            }
            self.movement_log.append(log_entry)
            
            logger.info(f"Started scanning paper {paper_id} at station {result['station_id']}")
            
            return {'success': True, **result}
            
        except Exception as e:
            logger.error(f"Failed to start scan for {paper_id}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def complete_scan(self, paper_id: str, success: bool = True, 
                     output_file: Optional[str] = None) -> Dict:
        """Complete a paper scan"""
        try:
            result = self.scanning_zone.complete_scan(paper_id, success, output_file)
            
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': 'COMPLETE_SCAN',
                'paper_id': paper_id,
                'success': success,
                'output_file': output_file,
                'status': 'success'
            }
            self.movement_log.append(log_entry)
            
            logger.info(f"Completed scan for paper {paper_id}: {'success' if success else 'failed'}")
            
            return {'success': True, **result}
            
        except Exception as e:
            logger.error(f"Failed to complete scan for {paper_id}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_scanning_status(self) -> Dict:
        """Get current status of the scanning zone"""
        return self.scanning_zone.get_status()
    
    def get_station_status(self, station_id: str) -> Dict:
        """Get status of a specific scanning station"""
        try:
            return self.scanning_zone.get_station_status(station_id)
        except Exception as e:
            return {'error': str(e)}
    
    def get_available_stations(self, scanner_type: Optional[str] = None) -> List[Dict]:
        """Get list of available scanning stations"""
        scanner_enum = ScannerType(scanner_type) if scanner_type else None
        available = []
        
        for station in self.scanning_zone.stations:
            if station.is_available:
                if scanner_enum is None or station.scanner_type == scanner_enum:
                    available.append({
                        'station_id': station.station_id,
                        'scanner_type': station.scanner_type.value,
                        'scanned_today': station.papers_scanned_today
                    })
        
        return available
    
    def move_papers_to_qc(self, paper_ids: Optional[List[str]] = None) -> Dict:
        """
        Move scanned papers to QC zone
        Enforces unidirectional flow: Scanning (➌) → QC (➍)
        
        Args:
            paper_ids: Optional list of specific paper IDs, or None for all scanned papers
            
        Returns:
            Movement confirmation
        """
        try:
            # Validate flow direction
            validation = self.validate_movement(ZoneType.SCANNING, ZoneType.QC)
            if not validation['allowed']:
                return {'success': False, 'error': validation['reason']}
            
            # Get papers to move
            if paper_ids:
                papers = [self.scanning_zone.get_paper(pid) for pid in paper_ids]
                papers = [p for p in papers if p is not None]
            else:
                papers = self.scanning_zone.scanned_papers.copy()
            
            if not papers:
                return {
                    'success': False,
                    'error': 'No papers available to move to QC'
                }
            
            # Remove from scanning zone
            for paper in papers:
                if paper in self.scanning_zone.scanned_papers:
                    self.scanning_zone.scanned_papers.remove(paper)
            
            # Receive in QC zone
            self.qc_zone.receive_papers(papers)
            
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': 'MOVE_TO_QC',
                'paper_count': len(papers),
                'paper_ids': [p.paper_id for p in papers],
                'from_zone': ZoneType.SCANNING.value,
                'to_zone': ZoneType.QC.value,
                'flow': '➌ → ➍',
                'status': 'success'
            }
            self.movement_log.append(log_entry)
            
            logger.info(f"Moved {len(papers)} papers to QC zone (➌ → ➍)")
            
            return {
                'success': True,
                'papers_moved': len(papers),
                'paper_ids': [p.paper_id for p in papers],
                'flow_direction': '➌ Scanning → ➍ QC',
                'next_step': 'Start QC checks'
            }
            
        except Exception as e:
            logger.error(f"Failed to move papers to QC: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def start_qc_check(self, paper_id: str, checked_by: str) -> Dict:
        """Start QC check for a paper"""
        try:
            result = self.qc_zone.start_qc_check(paper_id, checked_by)
            
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': 'START_QC_CHECK',
                'paper_id': paper_id,
                'checked_by': checked_by,
                'status': 'success'
            }
            self.movement_log.append(log_entry)
            
            logger.info(f"Started QC check for paper {paper_id} by {checked_by}")
            
            return {'success': True, **result}
            
        except Exception as e:
            logger.error(f"Failed to start QC check for {paper_id}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def complete_qc_check(self, paper_id: str, checked_by: str, passed: bool,
                         issues: Optional[List[str]] = None, notes: str = "",
                         needs_rescan: bool = False) -> Dict:
        """Complete QC check for a paper"""
        try:
            result = self.qc_zone.complete_qc_check(
                paper_id, checked_by, passed, issues, notes, needs_rescan
            )
            
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': 'COMPLETE_QC_CHECK',
                'paper_id': paper_id,
                'checked_by': checked_by,
                'passed': passed,
                'needs_rescan': needs_rescan,
                'status': 'success'
            }
            self.movement_log.append(log_entry)
            
            logger.info(f"QC check for paper {paper_id}: {'PASSED' if passed else 'FAILED'}")
            
            return {'success': True, **result}
            
        except Exception as e:
            logger.error(f"Failed to complete QC check for {paper_id}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def send_for_rescan(self, paper_id: str) -> Dict:
        """Send a failed QC paper back for rescanning"""
        try:
            paper = self.qc_zone.send_for_rescan(paper_id)
            
            # Add back to scanning zone
            self.scanning_zone.receive_papers([paper])
            
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': 'SEND_FOR_RESCAN',
                'paper_id': paper_id,
                'rescan_count': paper.metadata.get('rescan_count', 1),
                'status': 'success'
            }
            self.movement_log.append(log_entry)
            
            logger.info(f"Paper {paper_id} sent for rescan (attempt #{paper.metadata.get('rescan_count', 1)})")
            
            return {
                'success': True,
                'paper_id': paper.paper_id,
                'status': paper.status.value,
                'rescan_count': paper.metadata.get('rescan_count', 1),
                'next_step': 'Rescan paper'
            }
            
        except Exception as e:
            logger.error(f"Failed to send paper {paper_id} for rescan: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_qc_status(self) -> Dict:
        """Get current status of the QC zone"""
        return self.qc_zone.get_status()
    
    def get_qc_result(self, paper_id: str) -> Optional[Dict]:
        """Get QC result for a specific paper"""
        result = self.qc_zone.get_qc_result(paper_id)
        if result is None:
            return None
        
        return {
            'paper_id': result.paper_id,
            'checked_by': result.checked_by,
            'checked_at': result.checked_at.isoformat(),
            'passed': result.passed,
            'issues': [i.value for i in result.issues],
            'notes': result.notes,
            'needs_rescan': result.needs_rescan
        }
    
    # ============== OUTPUT RACK OPERATIONS ==============
    
    def move_paper_to_output(self, paper_id: str, disposition: OutputDisposition) -> Dict:
        """
        Move a processed paper from QC to output rack
        Enforces unidirectional flow: QC (➍) → Output (➎) - FINAL ZONE
        
        Args:
            paper_id: Paper identifier
            disposition: What to do with paper (return/shred/archive)
            
        Returns:
            Movement confirmation with bin assignment
        """
        try:
            # Validate flow direction
            validation = self.validate_movement(ZoneType.QC, ZoneType.OUTPUT)
            if not validation['allowed']:
                return {'success': False, 'error': validation['reason']}
            
            # Find paper in QC zone
            paper = None
            for p in self.qc_zone.passed_papers:
                if p.paper_id == paper_id:
                    paper = p
                    break
            
            if paper is None:
                return {'success': False, 'error': 'Paper not found in QC passed papers'}
            
            # Move to output rack
            if self.output_rack.receive_processed_paper(paper, disposition):
                self.qc_zone.passed_papers.remove(paper)
                self.qc_zone.papers.remove(paper)
                
                log_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'action': 'MOVE_TO_OUTPUT',
                    'paper_id': paper_id,
                    'from_zone': ZoneType.QC.value,
                    'to_zone': ZoneType.OUTPUT.value,
                    'flow': '➍ → ➎',
                    'disposition': disposition.value,
                    'status': 'success'
                }
                self.movement_log.append(log_entry)
                
                logger.info(f"Paper {paper_id} moved to output rack for {disposition.value} (➍ → ➎ FINAL)")
                
                return {
                    'success': True,
                    'paper_id': paper.paper_id,
                    'disposition': disposition.value,
                    'status': paper.status.value,
                    'flow_direction': '➍ QC → ➎ Output (FINAL)',
                    'next_step': f'Paper awaiting {disposition.value}'
                }
            else:
                return {'success': False, 'error': 'Output rack at capacity'}
                
        except Exception as e:
            logger.error(f"Failed to move paper {paper_id} to output: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def mark_bin_returned(self, bin_id: str) -> Dict:
        """
        Mark an entire bin as returned to customer
        
        Args:
            bin_id: Bin identifier
            
        Returns:
            Confirmation with paper count
        """
        try:
            # Find bin
            target_bin = None
            for bin in self.output_rack.bins:
                if bin.bin_id == bin_id:
                    target_bin = bin
                    break
            
            if target_bin is None:
                return {'success': False, 'error': 'Bin not found'}
            
            paper_count = len(target_bin.papers)
            
            if self.output_rack.mark_bin_returned(bin_id):
                log_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'action': 'MARK_RETURNED',
                    'bin_id': bin_id,
                    'paper_count': paper_count,
                    'zone': ZoneType.OUTPUT.value,
                    'status': 'success'
                }
                self.movement_log.append(log_entry)
                
                logger.info(f"Bin {bin_id} marked as returned ({paper_count} papers)")
                
                return {
                    'success': True,
                    'bin_id': bin_id,
                    'paper_count': paper_count,
                    'status': 'returned'
                }
            else:
                return {'success': False, 'error': 'Failed to mark bin as returned'}
                
        except Exception as e:
            logger.error(f"Failed to mark bin {bin_id} as returned: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def mark_bin_shredded(self, bin_id: str) -> Dict:
        """
        Mark an entire bin as shredded
        
        Args:
            bin_id: Bin identifier
            
        Returns:
            Confirmation with paper count
        """
        try:
            # Find bin
            target_bin = None
            for bin in self.output_rack.bins:
                if bin.bin_id == bin_id:
                    target_bin = bin
                    break
            
            if target_bin is None:
                return {'success': False, 'error': 'Bin not found'}
            
            paper_count = len(target_bin.papers)
            
            if self.output_rack.mark_bin_shredded(bin_id):
                log_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'action': 'MARK_SHREDDED',
                    'bin_id': bin_id,
                    'paper_count': paper_count,
                    'zone': ZoneType.OUTPUT.value,
                    'status': 'success'
                }
                self.movement_log.append(log_entry)
                
                logger.info(f"Bin {bin_id} marked as shredded ({paper_count} papers)")
                
                return {
                    'success': True,
                    'bin_id': bin_id,
                    'paper_count': paper_count,
                    'status': 'shredded'
                }
            else:
                return {'success': False, 'error': 'Failed to mark bin as shredded'}
                
        except Exception as e:
            logger.error(f"Failed to mark bin {bin_id} as shredded: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_output_status(self) -> Dict:
        """Get current status of the output rack"""
        return self.output_rack.get_status()
    
    def get_output_bins_by_disposition(self, disposition: OutputDisposition) -> List[Dict]:
        """Get all bins for a specific disposition"""
        bins = self.output_rack.get_bins_by_disposition(disposition)
        return [bin.get_status() for bin in bins]
    
    def get_active_output_bins(self) -> List[Dict]:
        """Get all active (unprocessed) bins"""
        bins = self.output_rack.get_active_bins()
        return [bin.get_status() for bin in bins]
