"""
Physical Zones Management
Handles the physical workflow zones for paper processing
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Set
from enum import Enum
from dataclasses import dataclass, field


class ZoneType(Enum):
    """Physical zone types in the workflow - LEFT TO RIGHT FLOW ONLY"""
    INTAKE = "intake"           # ➊ 📥 First zone
    PREP = "prep"               # ➋ 🔧 Second zone
    SCANNING = "scanning"       # ➌ 📸 Third zone
    QC = "qc"                   # ➍ ✅ Fourth zone
    OUTPUT = "output"           # ➎ 📤 Fifth zone (FINAL)
    SORTING = "sorting"         # Future use
    PROCESSING = "processing"   # Future use
    STORAGE = "storage"         # Future use
    
    def get_order(self) -> int:
        """Get the sequential order of this zone (lower = earlier in flow)"""
        order_map = {
            ZoneType.INTAKE: 1,
            ZoneType.PREP: 2,
            ZoneType.SCANNING: 3,
            ZoneType.QC: 4,
            ZoneType.OUTPUT: 5,
            ZoneType.SORTING: 99,
            ZoneType.PROCESSING: 99,
            ZoneType.STORAGE: 99
        }
        return order_map.get(self, 999)
    
    def get_icon(self) -> str:
        """Get visual icon for this zone"""
        icons = {
            ZoneType.INTAKE: "📥",
            ZoneType.PREP: "🔧",
            ZoneType.SCANNING: "📸",
            ZoneType.QC: "✅",
            ZoneType.OUTPUT: "📤",
            ZoneType.SORTING: "📋",
            ZoneType.PROCESSING: "⚙️",
            ZoneType.STORAGE: "📦"
        }
        return icons.get(self, "❓")
    
    def get_next_zone(self) -> Optional['ZoneType']:
        """Get the next zone in the workflow (enforces left-to-right flow)"""
        flow_map = {
            ZoneType.INTAKE: ZoneType.PREP,
            ZoneType.PREP: ZoneType.SCANNING,
            ZoneType.SCANNING: ZoneType.QC,
            ZoneType.QC: ZoneType.OUTPUT,
            ZoneType.OUTPUT: None  # Terminal zone
        }
        return flow_map.get(self)
    
    def get_previous_zone(self) -> Optional['ZoneType']:
        """Get the previous zone (for rescan/return flows only)"""
        flow_map = {
            ZoneType.PREP: ZoneType.INTAKE,
            ZoneType.SCANNING: ZoneType.PREP,
            ZoneType.QC: ZoneType.SCANNING,
            ZoneType.OUTPUT: ZoneType.QC,
            ZoneType.INTAKE: None  # Starting zone
        }
        return flow_map.get(self)
    
    def can_move_to(self, target_zone: 'ZoneType') -> bool:
        """Check if movement to target zone is allowed (forward only, or back to scanning for rescan)"""
        # Forward movement - always allowed to next zone
        if target_zone == self.get_next_zone():
            return True
        # Special case: QC can send back to scanning for rescan
        if self == ZoneType.QC and target_zone == ZoneType.SCANNING:
            return True
        # All other movements blocked
        return False


class PaperStatus(Enum):
    """Status of papers in the system"""
    RECEIVED = "received"
    LOGGED = "logged"
    IN_QUEUE = "in_queue"
    UNBOXING = "unboxing"
    SORTING_PREP = "sorting_prep"
    STAPLE_REMOVAL = "staple_removal"
    PREP_COMPLETE = "prep_complete"
    SCANNING = "scanning"
    SCAN_COMPLETE = "scan_complete"
    SCAN_FAILED = "scan_failed"
    QC_REVIEW = "qc_review"
    QC_PASSED = "qc_passed"
    QC_FAILED = "qc_failed"
    RESCANNING = "rescanning"
    PROCESSING = "processing"
    PROCESSED = "processed"
    SORTED = "sorted"
    AWAITING_RETURN = "awaiting_return"
    AWAITING_SHREDDING = "awaiting_shredding"
    RETURNED = "returned"
    SHREDDED = "shredded"
    COMPLETE = "complete"


class StateTransitionError(Exception):
    """Raised when an invalid paper status transition is attempted."""
    pass


# Allowed status transitions (forward-only with explicit rescan flow)
ALLOWED_TRANSITIONS = {
    PaperStatus.RECEIVED: {PaperStatus.LOGGED},
    PaperStatus.LOGGED: {PaperStatus.IN_QUEUE},  # queued for prep
    PaperStatus.IN_QUEUE: {PaperStatus.UNBOXING, PaperStatus.SCANNING, PaperStatus.RESCANNING},  # depending on zone context
    PaperStatus.UNBOXING: {PaperStatus.SORTING_PREP},
    PaperStatus.SORTING_PREP: {PaperStatus.STAPLE_REMOVAL, PaperStatus.PREP_COMPLETE},
    PaperStatus.STAPLE_REMOVAL: {PaperStatus.PREP_COMPLETE},
    PaperStatus.PREP_COMPLETE: {PaperStatus.IN_QUEUE, PaperStatus.SCANNING},
    PaperStatus.SCANNING: {PaperStatus.SCAN_COMPLETE, PaperStatus.SCAN_FAILED},
    PaperStatus.SCAN_FAILED: {PaperStatus.RESCANNING},  # explicit rescan enqueue
    PaperStatus.RESCANNING: {PaperStatus.SCANNING},
    PaperStatus.SCAN_COMPLETE: {PaperStatus.QC_REVIEW},
    PaperStatus.QC_REVIEW: {PaperStatus.QC_PASSED, PaperStatus.QC_FAILED},
    PaperStatus.QC_FAILED: {PaperStatus.RESCANNING},
    PaperStatus.QC_PASSED: {PaperStatus.PROCESSED, PaperStatus.PROCESSING},
    PaperStatus.PROCESSING: {PaperStatus.PROCESSED},
    PaperStatus.PROCESSED: {PaperStatus.AWAITING_RETURN, PaperStatus.AWAITING_SHREDDING, PaperStatus.COMPLETE},
    PaperStatus.AWAITING_RETURN: {PaperStatus.RETURNED},
    PaperStatus.AWAITING_SHREDDING: {PaperStatus.SHREDDED},
    PaperStatus.RETURNED: {PaperStatus.COMPLETE},
    PaperStatus.SHREDDED: {PaperStatus.COMPLETE},
    PaperStatus.COMPLETE: set(),
}


def validate_status_transition(current: PaperStatus, new: PaperStatus) -> None:
    """Validate a transition or raise StateTransitionError.

    Args:
        current: Current paper status.
        new: Desired new paper status.
    """
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if new not in allowed:
        raise StateTransitionError(f"Invalid transition {current.value} -> {new.value}. Allowed: {[s.value for s in allowed]}")


class PhysicalTool(Enum):
    """Physical tools/equipment used across zones"""
    BARCODE_PRINTER = "barcode_printer"
    SEPARATOR_SHEETS = "separator_sheets"
    CART = "cart"
    GLOVES = "gloves"
    SHRED_BIN = "shred_bin"


class SecurityControl(Enum):
    """Physical security controls present in zones"""
    LOCKED_CAGE = "locked_cage"
    CAMERA = "camera"
    RESTRICTED_BADGE = "restricted_badge"


class OutputDisposition(Enum):
    """Disposition options for processed documents"""
    RETURN = "return"  # Return to owner
    SHRED = "shred"    # Confidential shredding
    ARCHIVE = "archive"  # Long-term storage


class ScannerType(Enum):
    """Types of scanning equipment"""
    ADF = "adf"  # Automatic Document Feeder
    WORKSTATION = "workstation"  # Manual scanning workstation


@dataclass
class Box:
    """Represents a physical box containing papers"""
    box_id: str
    received_at: datetime
    status: PaperStatus
    current_zone: ZoneType
    paper_count: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    
    def log_receipt(self, paper_count: int, notes: str = "") -> None:
        """Log the receipt of the box in intake zone"""
        self.paper_count = paper_count
        self.status = PaperStatus.LOGGED
        self.notes = notes
        self.metadata['logged_at'] = datetime.now().isoformat()


@dataclass
class IntakeZone:
    """
    Intake Zone - Receiving and logging boxes
    Purpose: Move and control paper safely
    """
    zone_id: str = "INTAKE-01"
    zone_type: ZoneType = ZoneType.INTAKE
    boxes: List[Box] = field(default_factory=list)
    capacity: int = 50
    required_tools: List[PhysicalTool] = field(default_factory=lambda: [
        PhysicalTool.BARCODE_PRINTER,
        PhysicalTool.CART,
        PhysicalTool.GLOVES
    ])
    security_controls: List[SecurityControl] = field(default_factory=lambda: [
        SecurityControl.CAMERA,
        SecurityControl.RESTRICTED_BADGE
    ])
    
    def receive_box(self, box_id: str) -> Box:
        """
        Receive a new box in the intake zone
        
        Args:
            box_id: Unique identifier for the box
            
        Returns:
            Box object representing the received box
        """
        if len(self.boxes) >= self.capacity:
            raise ValueError(f"Intake zone at capacity ({self.capacity} boxes)")
        
        box = Box(
            box_id=box_id,
            received_at=datetime.now(),
            status=PaperStatus.RECEIVED,
            current_zone=ZoneType.INTAKE
        )
        self.boxes.append(box)
        return box
    
    def log_box(self, box_id: str, paper_count: int, notes: str = "") -> Box:
        """
        Log details of a received box
        
        Args:
            box_id: Box identifier
            paper_count: Number of papers in the box
            notes: Additional notes about the box
            
        Returns:
            Updated Box object
        """
        box = self.get_box(box_id)
        if box is None:
            raise ValueError(f"Box {box_id} not found in intake zone")
        
        box.log_receipt(paper_count, notes)
        return box
    
    def get_box(self, box_id: str) -> Optional[Box]:
        """Retrieve a box by its ID"""
        for box in self.boxes:
            if box.box_id == box_id:
                return box
        return None
    
    def get_logged_boxes(self) -> List[Box]:
        """Get all boxes that have been logged and are ready for next stage"""
        return [box for box in self.boxes if box.status == PaperStatus.LOGGED]
    
    def move_box_to_next_zone(self, box_id: str, next_zone: ZoneType) -> Box:
        """
        Move a logged box to the next zone
        
        Args:
            box_id: Box identifier
            next_zone: Destination zone
            
        Returns:
            Box object with updated zone
        """
        box = self.get_box(box_id)
        if box is None:
            raise ValueError(f"Box {box_id} not found")
        
        if box.status != PaperStatus.LOGGED:
            raise ValueError(f"Box {box_id} must be logged before moving")
        
        box.current_zone = next_zone
        box.status = PaperStatus.IN_QUEUE
        box.metadata['moved_at'] = datetime.now().isoformat()
        self.boxes.remove(box)
        
        return box
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the intake zone"""
        total = len(self.boxes)
        received = len([b for b in self.boxes if b.status == PaperStatus.RECEIVED])
        logged = len([b for b in self.boxes if b.status == PaperStatus.LOGGED])
        # Provide backward-compatible aliases expected by tests/UI:
        # boxes_received -> total boxes currently in intake (after receive/log)
        # boxes_logged -> number of boxes fully logged and ready for next stage
        return {
            'zone_id': self.zone_id,
            'zone_type': self.zone_type.value,
            'total_boxes': total,
            'boxes_received': total,          # alias for compatibility
            'boxes_logged': logged,           # alias for compatibility
            'capacity': self.capacity,
            'available_space': self.capacity - total,
            'received_count': received,
            'logged_count': logged,
            'required_tools': [t.value for t in self.required_tools],
            'security_controls': [s.value for s in self.security_controls]
        }

    def verify_tools(self, available: Set[PhysicalTool]) -> Dict[str, Any]:
        """Check whether required tools are available."""
        missing = [t.value for t in self.required_tools if t not in available]
        return {
            'zone_id': self.zone_id,
            'missing_tools': missing,
            'compliant': len(missing) == 0
        }

    def verify_security(self, present: Set[SecurityControl]) -> Dict[str, Any]:
        """Check whether required security controls are present."""
        missing = [s.value for s in self.security_controls if s not in present]
        return {
            'zone_id': self.zone_id,
            'missing_security_controls': missing,
            'compliant': len(missing) == 0
        }


@dataclass
class Paper:
    """Represents an individual paper document"""
    paper_id: str
    box_id: str
    status: PaperStatus
    current_zone: ZoneType
    has_staples: bool = True
    pages: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    def advance_status(self, new_status: PaperStatus, *, force: bool = False) -> None:
        """Advance to a new status with FSM enforcement.

        Args:
            new_status: target status.
            force: bypass validation (emergency/manual override).
        """
        if not force:
            validate_status_transition(self.status, new_status)
        self.status = new_status
        self.metadata.setdefault('status_history', []).append({
            'from': self.metadata.get('status_history', [])[-1]['to'] if self.metadata.get('status_history') else None,
            'to': new_status.value,
            'at': datetime.now().isoformat()
        })


@dataclass
class PrepZone:
    """
    Prep Zone - Unboxing, sorting, and removing staples
    Purpose: Prepare papers for scanning by removing physical obstacles
    """
    zone_id: str = "PREP-01"
    zone_type: ZoneType = ZoneType.PREP
    boxes: List[Box] = field(default_factory=list)
    papers: List[Paper] = field(default_factory=list)
    capacity: int = 30
    required_tools: List[PhysicalTool] = field(default_factory=lambda: [
        PhysicalTool.SEPARATOR_SHEETS,
        PhysicalTool.CART,
        PhysicalTool.GLOVES
    ])
    security_controls: List[SecurityControl] = field(default_factory=lambda: [
        SecurityControl.CAMERA,
        SecurityControl.RESTRICTED_BADGE
    ])
    
    def receive_box(self, box: Box) -> Box:
        """
        Receive a box from intake zone
        
        Args:
            box: Box object from intake zone
            
        Returns:
            Box object now in prep zone
        """
        if len(self.boxes) >= self.capacity:
            raise ValueError(f"Prep zone at capacity ({self.capacity} boxes)")
        
        # Must be coming from intake and already queued for prep
            # Require that the box originated from the intake zone and is marked IN_QUEUE
            if not (box.current_zone == ZoneType.INTAKE and box.status == PaperStatus.IN_QUEUE):
                raise ValueError(f"Box must originate from intake zone and have status IN_QUEUE")
        
        box.current_zone = ZoneType.PREP
        box.status = PaperStatus.UNBOXING
        box.metadata['prep_received_at'] = datetime.now().isoformat()
        self.boxes.append(box)
        return box
    
    def start_unboxing(self, box_id: str) -> Dict[str, Any]:
        """
        Start unboxing process for a box
        
        Args:
            box_id: Box identifier
            
        Returns:
            Unboxing details
        """
        box = self.get_box(box_id)
        if box is None:
            raise ValueError(f"Box {box_id} not found in prep zone")
        
        box.status = PaperStatus.UNBOXING
        box.metadata['unboxing_started_at'] = datetime.now().isoformat()
        
        return {
            'box_id': box_id,
            'status': 'unboxing_started',
            'expected_papers': box.paper_count
        }
    
    def add_paper_from_box(self, box_id: str, paper_id: str, 
                          has_staples: bool = True, pages: int = 1) -> Paper:
        """
        Add a paper from unboxing process
        
        Args:
            box_id: Source box identifier
            paper_id: Unique paper identifier
            has_staples: Whether paper has staples
            pages: Number of pages
            
        Returns:
            Paper object
        """
        box = self.get_box(box_id)
        if box is None:
            raise ValueError(f"Box {box_id} not found")
        
        paper = Paper(
            paper_id=paper_id,
            box_id=box_id,
            status=PaperStatus.SORTING_PREP,
            current_zone=ZoneType.PREP,
            has_staples=has_staples,
            pages=pages
        )
        self.papers.append(paper)
        return paper
    
    def remove_staples(self, paper_id: str) -> Paper:
        """
        Remove staples from a paper
        
        Args:
            paper_id: Paper identifier
            
        Returns:
            Updated paper object
        """
        paper = self.get_paper(paper_id)
        if paper is None:
            raise ValueError(f"Paper {paper_id} not found in prep zone")
        
        if not paper.has_staples:
            raise ValueError(f"Paper {paper_id} has no staples")
        
        paper.has_staples = False
        paper.status = PaperStatus.STAPLE_REMOVAL
        paper.metadata['staples_removed_at'] = datetime.now().isoformat()
        
        return paper
    
    def mark_paper_ready(self, paper_id: str) -> Paper:
        """
        Mark a paper as ready for scanning
        
        Args:
            paper_id: Paper identifier
            
        Returns:
            Updated paper object
        """
        paper = self.get_paper(paper_id)
        if paper is None:
            raise ValueError(f"Paper {paper_id} not found")
        
        if paper.has_staples:
            raise ValueError(f"Paper {paper_id} still has staples - remove them first")
        
        paper.status = PaperStatus.PREP_COMPLETE
        paper.metadata['prep_completed_at'] = datetime.now().isoformat()
        
        return paper
    
    def complete_box_prep(self, box_id: str) -> Box:
        """
        Mark entire box as prep complete
        
        Args:
            box_id: Box identifier
            
        Returns:
            Updated box object
        """
        box = self.get_box(box_id)
        if box is None:
            raise ValueError(f"Box {box_id} not found")
        
        # Check if all papers from this box are ready
        box_papers = [p for p in self.papers if p.box_id == box_id]
        incomplete = [p for p in box_papers if p.status != PaperStatus.PREP_COMPLETE]
        
        if incomplete:
            raise ValueError(
                f"Box {box_id} has {len(incomplete)} papers not ready. "
                f"Complete prep for all papers first."
            )
        
        box.status = PaperStatus.PREP_COMPLETE
        box.metadata['prep_completed_at'] = datetime.now().isoformat()
        
        return box
    
    def get_box(self, box_id: str) -> Optional[Box]:
        """Retrieve a box by its ID"""
        for box in self.boxes:
            if box.box_id == box_id:
                return box
        return None
    
    def get_paper(self, paper_id: str) -> Optional[Paper]:
        """Retrieve a paper by its ID"""
        for paper in self.papers:
            if paper.paper_id == paper_id:
                return paper
        return None
    
    def get_papers_needing_staple_removal(self) -> List[Paper]:
        """Get all papers that still have staples"""
        return [p for p in self.papers if p.has_staples]
    
    def get_ready_papers(self) -> List[Paper]:
        """Get all papers ready for scanning"""
        return [p for p in self.papers if p.status == PaperStatus.PREP_COMPLETE]
    
    def move_papers_to_scanning(self, box_id: str) -> List[Paper]:
        """
        Move all ready papers from a box to scanning
        
        Args:
            box_id: Box identifier
            
        Returns:
            List of papers moved to scanning
        """
        box = self.get_box(box_id)
        if box is None:
            raise ValueError(f"Box {box_id} not found")
        
        if box.status != PaperStatus.PREP_COMPLETE:
            raise ValueError(f"Box {box_id} prep not complete")
        
        box_papers = [p for p in self.papers if p.box_id == box_id 
                     and p.status == PaperStatus.PREP_COMPLETE]
        
        for paper in box_papers:
            paper.current_zone = ZoneType.SCANNING
            paper.status = PaperStatus.IN_QUEUE
            paper.metadata['moved_to_scanning_at'] = datetime.now().isoformat()
            self.papers.remove(paper)
        
        # Remove box from prep zone
        self.boxes.remove(box)
        
        return box_papers
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the prep zone"""
        return {
            'zone_id': self.zone_id,
            'zone_type': self.zone_type.value,
            'total_boxes': len(self.boxes),
            'capacity': self.capacity,
            'available_space': self.capacity - len(self.boxes),
            'total_papers': len(self.papers),
            'papers_with_staples': len([p for p in self.papers if p.has_staples]),
            'papers_ready': len([p for p in self.papers if p.status == PaperStatus.PREP_COMPLETE]),
            'boxes_in_prep': len([b for b in self.boxes if b.status != PaperStatus.PREP_COMPLETE]),
            'boxes_complete': len([b for b in self.boxes if b.status == PaperStatus.PREP_COMPLETE]),
            'required_tools': [t.value for t in self.required_tools],
            'security_controls': [s.value for s in self.security_controls]
        }

    def verify_tools(self, available: Set[PhysicalTool]) -> Dict[str, Any]:
        missing = [t.value for t in self.required_tools if t not in available]
        return {
            'zone_id': self.zone_id,
            'missing_tools': missing,
            'compliant': len(missing) == 0
        }

    def verify_security(self, present: Set[SecurityControl]) -> Dict[str, Any]:
        missing = [s.value for s in self.security_controls if s not in present]
        return {
            'zone_id': self.zone_id,
            'missing_security_controls': missing,
            'compliant': len(missing) == 0
        }


@dataclass
class ScanStation:
    """Represents a scanning station (ADF or workstation)"""
    station_id: str
    scanner_type: ScannerType
    is_available: bool = True
    current_paper: Optional[Paper] = None
    papers_scanned_today: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def start_scan(self, paper: Paper) -> None:
        """Start scanning a paper at this station"""
        if not self.is_available:
            raise ValueError(f"Station {self.station_id} is busy")
        
        self.is_available = False
        self.current_paper = paper
        self.metadata['current_scan_started_at'] = datetime.now().isoformat()
    
    def complete_scan(self, success: bool = True) -> Optional[Paper]:
        """Complete the current scan"""
        if self.current_paper is None:
            return None
        
        paper = self.current_paper
        self.current_paper = None
        self.is_available = True
        
        if success:
            self.papers_scanned_today += 1
            self.metadata['last_scan_completed_at'] = datetime.now().isoformat()
        else:
            self.metadata['last_scan_failed_at'] = datetime.now().isoformat()
        
        return paper


@dataclass
class ScanningZone:
    """
    Scanning Zone - ADF and workstation scanning
    Purpose: Digitize physical papers with OCR-ready scans
    """
    zone_id: str = "SCAN-01"
    zone_type: ZoneType = ZoneType.SCANNING
    papers: List[Paper] = field(default_factory=list)
    stations: List[ScanStation] = field(default_factory=list)
    scanned_papers: List[Paper] = field(default_factory=list)
    capacity: int = 100  # Papers in queue
    required_tools: List[PhysicalTool] = field(default_factory=lambda: [
        PhysicalTool.SEPARATOR_SHEETS,
        PhysicalTool.GLOVES
    ])
    security_controls: List[SecurityControl] = field(default_factory=lambda: [
        SecurityControl.CAMERA,
        SecurityControl.RESTRICTED_BADGE
    ])
    
    def __post_init__(self):
        """Initialize default scanning stations"""
        if not self.stations:
            # Create 2 ADF stations and 1 workstation by default
            self.stations = [
                ScanStation(station_id="ADF-01", scanner_type=ScannerType.ADF),
                ScanStation(station_id="ADF-02", scanner_type=ScannerType.ADF),
                ScanStation(station_id="WS-01", scanner_type=ScannerType.WORKSTATION),
            ]
    
    def receive_papers(self, papers: List[Paper]) -> List[Paper]:
        """
        Receive papers from prep zone
        
        Args:
            papers: List of prepared papers
            
        Returns:
            List of papers now in scanning queue
        """
        if len(self.papers) + len(papers) > self.capacity:
            raise ValueError(
                f"Scanning queue at capacity. "
                f"Current: {len(self.papers)}, Incoming: {len(papers)}, Max: {self.capacity}"
            )
        
        for paper in papers:
            if paper.current_zone != ZoneType.SCANNING:
                paper.current_zone = ZoneType.SCANNING
            
            paper.status = PaperStatus.IN_QUEUE
            paper.metadata['scan_queue_at'] = datetime.now().isoformat()
            self.papers.append(paper)
        
        return papers
    
    def get_available_station(self, scanner_type: Optional[ScannerType] = None) -> Optional[ScanStation]:
        """
        Get an available scanning station
        
        Args:
            scanner_type: Specific scanner type required (optional)
            
        Returns:
            Available station or None
        """
        for station in self.stations:
            if station.is_available:
                if scanner_type is None or station.scanner_type == scanner_type:
                    return station
        return None
    
    def start_scan(self, paper_id: str, station_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Start scanning a paper
        
        Args:
            paper_id: Paper identifier
            station_id: Optional specific station ID
            
        Returns:
            Scan start details
        """
        paper = self.get_paper(paper_id)
        if paper is None:
            raise ValueError(f"Paper {paper_id} not found in scanning zone")
        
        if paper.status != PaperStatus.IN_QUEUE:
            raise ValueError(f"Paper {paper_id} not in queue for scanning")
        
        # Find station
        if station_id:
            station = next((s for s in self.stations if s.station_id == station_id), None)
            if station is None:
                raise ValueError(f"Station {station_id} not found")
            if not station.is_available:
                raise ValueError(f"Station {station_id} is busy")
        else:
            station = self.get_available_station()
            if station is None:
                raise ValueError("No available scanning stations")
        
        # Start scan
        station.start_scan(paper)
        paper.status = PaperStatus.SCANNING
        paper.metadata['scanning_station'] = station.station_id
        paper.metadata['scan_started_at'] = datetime.now().isoformat()
        
        return {
            'paper_id': paper_id,
            'station_id': station.station_id,
            'scanner_type': station.scanner_type.value,
            'status': 'scanning_started'
        }
    
    def complete_scan(self, paper_id: str, success: bool = True, 
                     output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Complete a paper scan
        
        Args:
            paper_id: Paper identifier
            success: Whether scan was successful
            output_file: Path to scanned file
            
        Returns:
            Scan completion details
        """
        paper = self.get_paper(paper_id)
        if paper is None:
            raise ValueError(f"Paper {paper_id} not found")
        
        if paper.status != PaperStatus.SCANNING:
            raise ValueError(f"Paper {paper_id} is not being scanned")
        
        # Find station with this paper
        station = next((s for s in self.stations if s.current_paper == paper), None)
        if station is None:
            raise ValueError(f"No station found scanning paper {paper_id}")
        
        # Complete at station
        station.complete_scan(success)
        
        # Update paper
        if success:
            # Enforce transition
            paper.advance_status(PaperStatus.SCAN_COMPLETE)
            paper.metadata['scan_completed_at'] = datetime.now().isoformat()
            if output_file:
                paper.metadata['scan_file'] = output_file
            
            # Move to scanned papers
            self.papers.remove(paper)
            self.scanned_papers.append(paper)
        else:
            # Preserve failure state; caller must explicitly queue for rescan
            paper.advance_status(PaperStatus.SCAN_FAILED)
            paper.metadata['scan_failed_at'] = datetime.now().isoformat()
        
        return {
            'paper_id': paper_id,
            'success': success,
            'status': paper.status.value,
            'output_file': output_file,
            'station_id': station.station_id
        }
    
    def retry_failed_scan(self, paper_id: str) -> Paper:
        """Put a failed scan back in queue"""
        paper = self.get_paper(paper_id)
        if paper is None:
            raise ValueError(f"Paper {paper_id} not found")
        if paper.status != PaperStatus.SCAN_FAILED:
            raise ValueError(f"Paper {paper_id} is not in SCAN_FAILED state")
        # Transition to RESCANNING queue then will go to SCANNING
        paper.advance_status(PaperStatus.RESCANNING)
        paper.metadata['retry_queued_at'] = datetime.now().isoformat()
        return paper
    
    def get_paper(self, paper_id: str) -> Optional[Paper]:
        """Retrieve a paper by its ID"""
        for paper in self.papers:
            if paper.paper_id == paper_id:
                return paper
        return None
    
    def get_queued_papers(self) -> List[Paper]:
        """Get all papers waiting in queue"""
        return [p for p in self.papers if p.status == PaperStatus.IN_QUEUE]
    
    def get_scanning_papers(self) -> List[Paper]:
        """Get all papers currently being scanned"""
        return [p for p in self.papers if p.status == PaperStatus.SCANNING]
    
    def get_station(self, station_id: str) -> Optional[ScanStation]:
        """Get a station by ID"""
        for station in self.stations:
            if station.station_id == station_id:
                return station
        return None
    
    def get_station_status(self, station_id: str) -> Dict[str, Any]:
        """Get status of a specific station"""
        station = self.get_station(station_id)
        if station is None:
            raise ValueError(f"Station {station_id} not found")
        
        return {
            'station_id': station.station_id,
            'scanner_type': station.scanner_type.value,
            'is_available': station.is_available,
            'current_paper': station.current_paper.paper_id if station.current_paper else None,
            'papers_scanned_today': station.papers_scanned_today,
            'metadata': station.metadata
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the scanning zone"""
        available_stations = len([s for s in self.stations if s.is_available])
        total_scanned = sum(s.papers_scanned_today for s in self.stations)
        
        return {
            'zone_id': self.zone_id,
            'zone_type': self.zone_type.value,
            'papers_in_queue': len([p for p in self.papers if p.status == PaperStatus.IN_QUEUE]),
            'papers_scanning': len([p for p in self.papers if p.status == PaperStatus.SCANNING]),
            'papers_scanned': len(self.scanned_papers),
            'total_papers': len(self.papers),
            'capacity': self.capacity,
            'available_space': self.capacity - len(self.papers),
            'total_stations': len(self.stations),
            'available_stations': available_stations,
            'busy_stations': len(self.stations) - available_stations,
            'papers_scanned_today': total_scanned,
            'stations': [
                {
                    'id': s.station_id,
                    'type': s.scanner_type.value,
                    'available': s.is_available,
                    'scanned_today': s.papers_scanned_today
                }
                for s in self.stations
            ],
            'required_tools': [t.value for t in self.required_tools],
            'security_controls': [s.value for s in self.security_controls]
        }

    def verify_tools(self, available: Set[PhysicalTool]) -> Dict[str, Any]:
        missing = [t.value for t in self.required_tools if t not in available]
        return {
            'zone_id': self.zone_id,
            'missing_tools': missing,
            'compliant': len(missing) == 0
        }

    def verify_security(self, present: Set[SecurityControl]) -> Dict[str, Any]:
        missing = [s.value for s in self.security_controls if s not in present]
        return {
            'zone_id': self.zone_id,
            'missing_security_controls': missing,
            'compliant': len(missing) == 0
        }


class QCIssueType(Enum):
    """Types of QC issues found"""
    POOR_QUALITY = "poor_quality"
    MISSING_PAGES = "missing_pages"
    BLURRY = "blurry"
    MISALIGNED = "misaligned"
    INCOMPLETE = "incomplete"
    OTHER = "other"


@dataclass
class QCResult:
    """Quality control check result"""
    paper_id: str
    checked_by: str
    checked_at: datetime
    passed: bool
    issues: List[QCIssueType] = field(default_factory=list)
    notes: str = ""
    needs_rescan: bool = False


@dataclass
class QCZone:
    """
    QC Zone - Visual quality checks and rescans
    Purpose: Ensure scan quality before processing
    """
    zone_id: str = "QC-01"
    zone_type: ZoneType = ZoneType.QC
    papers: List[Paper] = field(default_factory=list)
    qc_results: List[QCResult] = field(default_factory=list)
    failed_papers: List[Paper] = field(default_factory=list)
    passed_papers: List[Paper] = field(default_factory=list)
    capacity: int = 50
    required_tools: List[PhysicalTool] = field(default_factory=lambda: [
        PhysicalTool.SEPARATOR_SHEETS,
        PhysicalTool.GLOVES
    ])
    security_controls: List[SecurityControl] = field(default_factory=lambda: [
        SecurityControl.CAMERA,
        SecurityControl.RESTRICTED_BADGE
    ])
    
    def receive_papers(self, papers: List[Paper]) -> List[Paper]:
        """
        Receive papers from scanning zone for QC
        
        Args:
            papers: List of scanned papers
            
        Returns:
            List of papers now in QC queue
        """
        if len(self.papers) + len(papers) > self.capacity:
            raise ValueError(
                f"QC zone at capacity. "
                f"Current: {len(self.papers)}, Incoming: {len(papers)}, Max: {self.capacity}"
            )
        
        for paper in papers:
            paper.current_zone = ZoneType.QC
            paper.status = PaperStatus.QC_REVIEW
            paper.metadata['qc_received_at'] = datetime.now().isoformat()
            self.papers.append(paper)
        
        return papers
    
    def start_qc_check(self, paper_id: str, checked_by: str) -> Dict[str, Any]:
        """
        Start QC check for a paper
        
        Args:
            paper_id: Paper identifier
            checked_by: Name/ID of QC operator
            
        Returns:
            QC start confirmation
        """
        paper = self.get_paper(paper_id)
        if paper is None:
            raise ValueError(f"Paper {paper_id} not found in QC zone")
        
        if paper.status != PaperStatus.QC_REVIEW:
            raise ValueError(f"Paper {paper_id} not ready for QC")
        
        paper.metadata['qc_started_at'] = datetime.now().isoformat()
        paper.metadata['qc_checked_by'] = checked_by
        
        return {
            'paper_id': paper_id,
            'checked_by': checked_by,
            'scan_file': paper.metadata.get('scan_file'),
            'status': 'qc_check_started'
        }
    
    def complete_qc_check(self, paper_id: str, checked_by: str, passed: bool,
                         issues: Optional[List[str]] = None, notes: str = "",
                         needs_rescan: bool = False) -> Dict[str, Any]:
        """
        Complete QC check for a paper
        
        Args:
            paper_id: Paper identifier
            checked_by: Name/ID of QC operator
            passed: Whether QC check passed
            issues: List of issue types found
            notes: Additional notes
            needs_rescan: Whether paper needs to be rescanned
            
        Returns:
            QC completion details
        """
        paper = self.get_paper(paper_id)
        if paper is None:
            raise ValueError(f"Paper {paper_id} not found")
        
        # Convert issue strings to enum
        issue_enums = []
        if issues:
            for issue in issues:
                try:
                    issue_enums.append(QCIssueType(issue))
                except ValueError:
                    issue_enums.append(QCIssueType.OTHER)
        
        # Create QC result
        qc_result = QCResult(
            paper_id=paper_id,
            checked_by=checked_by,
            checked_at=datetime.now(),
            passed=passed,
            issues=issue_enums,
            notes=notes,
            needs_rescan=needs_rescan
        )
        self.qc_results.append(qc_result)
        
        # Update paper status
        if passed:
            paper.status = PaperStatus.QC_PASSED
            paper.metadata['qc_passed_at'] = datetime.now().isoformat()
            self.papers.remove(paper)
            self.passed_papers.append(paper)
        else:
            paper.status = PaperStatus.QC_FAILED
            paper.metadata['qc_failed_at'] = datetime.now().isoformat()
            paper.metadata['qc_issues'] = [i.value for i in issue_enums]
            paper.metadata['qc_notes'] = notes
            
            if needs_rescan:
                paper.status = PaperStatus.RESCANNING
            
            self.papers.remove(paper)
            self.failed_papers.append(paper)
        
        return {
            'paper_id': paper_id,
            'passed': passed,
            'status': paper.status.value,
            'issues': [i.value for i in issue_enums],
            'needs_rescan': needs_rescan,
            'next_action': 'Ready for processing' if passed else ('Rescan required' if needs_rescan else 'Manual review needed')
        }
    
    def send_for_rescan(self, paper_id: str) -> Paper:
        """
        Send a failed QC paper back for rescanning
        
        Args:
            paper_id: Paper identifier
            
        Returns:
            Paper object ready for rescan
        """
        paper = None
        for p in self.failed_papers:
            if p.paper_id == paper_id:
                paper = p
                break
        
        if paper is None:
            raise ValueError(f"Paper {paper_id} not found in failed papers")
        
        if paper.status != PaperStatus.QC_FAILED and paper.status != PaperStatus.RESCANNING:
            raise ValueError(f"Paper {paper_id} not in failed status")
        
        paper.status = PaperStatus.RESCANNING
        paper.current_zone = ZoneType.SCANNING
        paper.metadata['rescan_requested_at'] = datetime.now().isoformat()
        paper.metadata['rescan_count'] = paper.metadata.get('rescan_count', 0) + 1
        
        self.failed_papers.remove(paper)
        
        return paper
    
    def get_paper(self, paper_id: str) -> Optional[Paper]:
        """Retrieve a paper by its ID from any list"""
        for paper in self.papers + self.failed_papers + self.passed_papers:
            if paper.paper_id == paper_id:
                return paper
        return None
    
    def get_papers_in_review(self) -> List[Paper]:
        """Get all papers currently in QC review"""
        return [p for p in self.papers if p.status == PaperStatus.QC_REVIEW]
    
    def get_qc_result(self, paper_id: str) -> Optional[QCResult]:
        """Get QC result for a specific paper"""
        for result in self.qc_results:
            if result.paper_id == paper_id:
                return result
        return None
    
    def get_papers_needing_rescan(self) -> List[Paper]:
        """Get all papers that need to be rescanned"""
        return [p for p in self.failed_papers if p.status == PaperStatus.RESCANNING]
    
    def get_qc_statistics(self) -> Dict[str, Any]:
        """Get QC statistics"""
        total_checked = len(self.qc_results)
        passed_count = len([r for r in self.qc_results if r.passed])
        failed_count = len([r for r in self.qc_results if not r.passed])
        
        # Count issues by type
        issue_counts = {}
        for result in self.qc_results:
            for issue in result.issues:
                issue_counts[issue.value] = issue_counts.get(issue.value, 0) + 1
        
        return {
            'total_checked': total_checked,
            'passed': passed_count,
            'failed': failed_count,
            'pass_rate': (passed_count / total_checked * 100) if total_checked > 0 else 0,
            'issue_breakdown': issue_counts,
            'papers_needing_rescan': len(self.get_papers_needing_rescan())
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the QC zone"""
        return {
            'zone_id': self.zone_id,
            'zone_type': self.zone_type.value,
            'papers_in_review': len(self.get_papers_in_review()),
            'papers_passed': len(self.passed_papers),
            'papers_failed': len(self.failed_papers),
            'papers_needing_rescan': len(self.get_papers_needing_rescan()),
            'total_papers': len(self.papers),
            'capacity': self.capacity,
            'available_space': self.capacity - len(self.papers),
            'statistics': self.get_qc_statistics(),
            'required_tools': [t.value for t in self.required_tools],
            'security_controls': [s.value for s in self.security_controls]
        }

    def verify_tools(self, available: Set[PhysicalTool]) -> Dict[str, Any]:
        missing = [t.value for t in self.required_tools if t not in available]
        return {
            'zone_id': self.zone_id,
            'missing_tools': missing,
            'compliant': len(missing) == 0
        }

    def verify_security(self, present: Set[SecurityControl]) -> Dict[str, Any]:
        missing = [s.value for s in self.security_controls if s not in present]
        return {
            'zone_id': self.zone_id,
            'missing_security_controls': missing,
            'compliant': len(missing) == 0
        }


@dataclass
class OutputBin:
    """Represents a physical bin in the output rack"""
    bin_id: str
    disposition: OutputDisposition
    papers: List[Paper] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    capacity: int = 100
    
    def add_paper(self, paper: Paper) -> bool:
        """Add a paper to this bin"""
        if len(self.papers) >= self.capacity:
            return False
        self.papers.append(paper)
        return True
    
    def is_full(self) -> bool:
        """Check if bin is at capacity"""
        return len(self.papers) >= self.capacity
    
    def get_status(self) -> Dict[str, Any]:
        """Get bin status"""
        return {
            'bin_id': self.bin_id,
            'disposition': self.disposition.value,
            'paper_count': len(self.papers),
            'capacity': self.capacity,
            'is_full': self.is_full(),
            'created_at': self.created_at.isoformat(),
            'processed_at': self.processed_at.isoformat() if self.processed_at else None
        }


class OutputRack:
    """Output rack zone for processed papers awaiting return, shredding, or archiving"""
    
    def __init__(self, zone_id: str = "OUTPUT-001", capacity: int = 500):
        self.zone_id = zone_id
        self.zone_type = ZoneType.OUTPUT
        self.capacity = capacity
        self.bins: List[OutputBin] = []
        self.papers: List[Paper] = []
        self.completed_papers: List[Paper] = []  # Returned or shredded
        self.required_tools: List[PhysicalTool] = [PhysicalTool.BARCODE_PRINTER, PhysicalTool.SHRED_BIN]
        self.security_controls: List[SecurityControl] = [SecurityControl.LOCKED_CAGE, SecurityControl.CAMERA, SecurityControl.RESTRICTED_BADGE]
        
    def create_bin(self, disposition: OutputDisposition) -> OutputBin:
        """Create a new output bin for a specific disposition"""
        bin_id = f"BIN-{disposition.value.upper()}-{len(self.bins) + 1:03d}"
        new_bin = OutputBin(bin_id=bin_id, disposition=disposition)
        self.bins.append(new_bin)
        return new_bin
    
    def receive_processed_paper(self, paper: Paper, disposition: OutputDisposition) -> bool:
        """Receive a processed paper from QC and assign to appropriate bin"""
        if len(self.papers) >= self.capacity:
            return False
        
        # Find or create appropriate bin
        target_bin = None
        for bin in self.bins:
            if bin.disposition == disposition and not bin.is_full():
                target_bin = bin
                break
        
        if target_bin is None:
            target_bin = self.create_bin(disposition)
        
        # Update paper status and add to bin
        paper.status = PaperStatus.PROCESSED
        if disposition == OutputDisposition.RETURN:
            paper.status = PaperStatus.AWAITING_RETURN
        elif disposition == OutputDisposition.SHRED:
            paper.status = PaperStatus.AWAITING_SHREDDING
        
        if target_bin.add_paper(paper):
            self.papers.append(paper)
            paper.current_zone = self.zone_type
            return True
        return False
    
    def mark_bin_returned(self, bin_id: str) -> bool:
        """Mark all papers in a bin as returned"""
        for bin in self.bins:
            if bin.bin_id == bin_id and bin.disposition == OutputDisposition.RETURN:
                for paper in bin.papers:
                    paper.status = PaperStatus.RETURNED
                    self.completed_papers.append(paper)
                    self.papers.remove(paper)
                bin.processed_at = datetime.now()
                return True
        return False
    
    def mark_bin_shredded(self, bin_id: str) -> bool:
        """Mark all papers in a bin as shredded"""
        for bin in self.bins:
            if bin.bin_id == bin_id and bin.disposition == OutputDisposition.SHRED:
                for paper in bin.papers:
                    paper.status = PaperStatus.SHREDDED
                    self.completed_papers.append(paper)
                    self.papers.remove(paper)
                bin.processed_at = datetime.now()
                return True
        return False
    
    def get_bins_by_disposition(self, disposition: OutputDisposition) -> List[OutputBin]:
        """Get all bins for a specific disposition"""
        return [bin for bin in self.bins if bin.disposition == disposition]
    
    def get_active_bins(self) -> List[OutputBin]:
        """Get bins that haven't been processed yet"""
        return [bin for bin in self.bins if bin.processed_at is None]
    
    def get_papers_awaiting_return(self) -> List[Paper]:
        """Get papers waiting to be returned"""
        return [p for p in self.papers if p.status == PaperStatus.AWAITING_RETURN]
    
    def get_papers_awaiting_shredding(self) -> List[Paper]:
        """Get papers waiting to be shredded"""
        return [p for p in self.papers if p.status == PaperStatus.AWAITING_SHREDDING]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get output zone statistics"""
        return_bins = self.get_bins_by_disposition(OutputDisposition.RETURN)
        shred_bins = self.get_bins_by_disposition(OutputDisposition.SHRED)
        archive_bins = self.get_bins_by_disposition(OutputDisposition.ARCHIVE)
        
        return {
            'total_papers': len(self.papers),
            'awaiting_return': len(self.get_papers_awaiting_return()),
            'awaiting_shredding': len(self.get_papers_awaiting_shredding()),
            'completed': len(self.completed_papers),
            'total_bins': len(self.bins),
            'active_bins': len(self.get_active_bins()),
            'return_bins': len(return_bins),
            'shred_bins': len(shred_bins),
            'archive_bins': len(archive_bins)
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the output rack"""
        return {
            'zone_id': self.zone_id,
            'zone_type': self.zone_type.value,
            'total_papers': len(self.papers),
            'completed_papers': len(self.completed_papers),
            'capacity': self.capacity,
            'available_space': self.capacity - len(self.papers),
            'active_bins': len(self.get_active_bins()),
            'statistics': self.get_statistics(),
            'required_tools': [t.value for t in self.required_tools],
            'security_controls': [s.value for s in self.security_controls]
        }

    def verify_tools(self, available: Set[PhysicalTool]) -> Dict[str, Any]:
        missing = [t.value for t in self.required_tools if t not in available]
        return {
            'zone_id': self.zone_id,
            'missing_tools': missing,
            'compliant': len(missing) == 0
        }

    def verify_security(self, present: Set[SecurityControl]) -> Dict[str, Any]:
        missing = [s.value for s in self.security_controls if s not in present]
        return {
            'zone_id': self.zone_id,
            'missing_security_controls': missing,
            'compliant': len(missing) == 0
        }
