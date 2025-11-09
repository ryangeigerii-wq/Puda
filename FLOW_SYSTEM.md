# Unidirectional Flow System - Implementation Guide

## Overview
The paper processing system now enforces a **strict left-to-right unidirectional flow** to prevent mix-ups, confusion, and workflow errors.

## Visual Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  UNIDIRECTIONAL FLOW (No Backwards Movement)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ➊ 📥      →      ➋ 🔧      →      ➌ 📸      →      ➍ ✅      →      ➎ 📤    │
│   INTAKE          PREP         SCANNING         QC           OUTPUT        │
│   Receive         Unbox        Digitize        Check         Final         │
│   Boxes           Papers       Documents       Quality       Disposition   │
│                                                   ↓                         │
│                                              Rescan Only                    │
│                                              (QC → Scan)                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Core Principles

### 1. Left-to-Right Only
- Papers/boxes can ONLY move forward (left to right)
- No backwards movement except for QC rescan (special exception)
- Cannot skip zones

### 2. Zone Ordering
```
➊ Intake (order: 1)    - Starting point
➋ Prep (order: 2)      - Second step
➌ Scanning (order: 3)  - Third step
➍ QC (order: 4)        - Fourth step
➎ Output (order: 5)    - Final destination (terminal)
```

### 3. Allowed Movements
✅ **VALID:**
- Intake → Prep
- Prep → Scanning
- Scanning → QC
- QC → Output
- QC → Scanning (rescan exception)

❌ **BLOCKED:**
- Any backwards movement (except QC rescan)
- Skipping zones (e.g., Intake → Scanning)
- Output → anywhere (terminal zone)

## Implementation Details

### Zone Type Enhancements

Added methods to `ZoneType` enum in `zones.py`:

```python
def get_order(self) -> int:
    """Get the sequential order of this zone"""

def get_icon(self) -> str:
    """Get visual icon for this zone"""

def get_next_zone(self) -> Optional['ZoneType']:
    """Get the next zone in workflow"""

def get_previous_zone(self) -> Optional['ZoneType']:
    """Get the previous zone (for rescan only)"""

def can_move_to(self, target_zone: 'ZoneType') -> bool:
    """Check if movement to target zone is allowed"""
```

### Control System Enhancements

Added to `PaperControlSystem` in `control.py`:

```python
def get_workflow_status(self) -> Dict:
    """Get visual representation of entire workflow"""

def validate_movement(self, from_zone: ZoneType, to_zone: ZoneType) -> Dict:
    """Validate if movement is allowed (enforces left-to-right)"""
```

### Movement Validation

All movement methods now validate flow direction:

```python
# Validate flow direction
validation = self.validate_movement(ZoneType.INTAKE, ZoneType.PREP)
if not validation['allowed']:
    return {'success': False, 'error': validation['reason']}
```

## User Interface Integration

### 1. Workflow Visualizer CLI

New tool: `workflow_cli.py`

**Features:**
- Visual flow diagram
- Zone status display (left to right)
- System summary
- Flow validation testing
- Real-time capacity tracking

**Usage:**
```bash
python workflow_cli.py
# Or via Docker
.\docker-helper.ps1 workflow
```

**Menu Options:**
1. View Flow Diagram
2. View Zone Status
3. View System Summary
4. Test Flow Validation
5. View Complete Report
6. Exit

### 2. Updated Zone CLIs

All zone CLIs now show flow position:

**Intake CLI:**
```
➊ 📥 INTAKE → ➋ Prep → ➌ Scanning → ➍ QC → ➎ Output
```

**Shows:**
- Current position in flow
- Next zone destination
- Flow direction indicator

### 3. Enhanced Movement Responses

All movement operations now return flow information:

```python
{
    'success': True,
    'box_id': 'BOX-001',
    'flow_direction': '➊ Intake → ➋ Prep',
    'next_step': 'Start unboxing process'
}
```

## Visual Indicators

### Zone Icons
- 📥 Intake (receiving)
- 🔧 Prep (preparation)
- 📸 Scanning (digitization)
- ✅ QC (quality control)
- 📤 Output (final disposition)

### Status Indicators
- 🟢 Active zone (contains items)
- ⚪ Empty zone
- ✅ Valid movement
- ❌ Blocked movement
- ➡️ Flow direction

## API Examples

### Check Workflow Status
```python
from src.physical.control import PaperControlSystem

control = PaperControlSystem()
workflow = control.get_workflow_status()

print(workflow['flow'])
# Output: "➊ Intake → ➋ Prep → ➌ Scanning → ➍ QC → ➎ Output"

print(f"Total papers in system: {workflow['total_papers_in_system']}")
print(f"Completed papers: {workflow['completed_papers']}")
```

### Validate Movement
```python
from src.physical.zones import ZoneType

# Valid forward movement
result = control.validate_movement(ZoneType.INTAKE, ZoneType.PREP)
print(result['allowed'])  # True
print(result['reason'])   # "Valid forward movement: 📥 intake → 🔧 prep"

# Invalid backward movement
result = control.validate_movement(ZoneType.PREP, ZoneType.INTAKE)
print(result['allowed'])  # False
print(result['reason'])   # "❌ BLOCKED: Cannot move backwards..."
```

### Check Zone Order
```python
intake_order = ZoneType.INTAKE.get_order()  # 1
prep_order = ZoneType.PREP.get_order()      # 2
output_order = ZoneType.OUTPUT.get_order()  # 5

# Check next zone
next_zone = ZoneType.INTAKE.get_next_zone()
print(next_zone)  # ZoneType.PREP
```

## Benefits

### 1. Error Prevention
- No accidental backwards movement
- No skipping critical processing steps
- Clear validation messages

### 2. User Clarity
- Visual indicators show exact position
- Flow diagram always visible
- Next steps clearly indicated

### 3. Audit Trail
- All movements logged with flow direction
- Easy to verify correct workflow
- Movement history shows '➊ → ➋' format

### 4. System Integrity
- Enforced at code level (not just UI)
- Cannot bypass validation
- Special rescan flow properly handled

## Exception: QC Rescan Flow

The ONLY allowed backward movement:

```
➍ QC → ➌ Scanning (for rescanning failed papers)
```

**When allowed:**
- Paper failed QC inspection
- Issues detected (blurry, missing pages, etc.)
- Marked as needs_rescan

**Process:**
```python
# Paper fails QC
control.complete_qc_check(paper_id, operator, passed=False, 
                         issues=['blurry'], needs_rescan=True)

# Send back to scanning (special exception)
control.send_for_rescan(paper_id)
# This is validated and allowed
```

## Testing

### Test Workflow Visualizer
```bash
# In Docker
.\docker-helper.ps1 workflow

# Select option 4: Test Flow Validation
# Shows all valid and invalid movements
```

### Test in Code
```python
# Run the test suite
python test_output_zone.py

# All movements will show flow direction:
# "Box BOX-001 moved to prep zone (➊ → ➋)"
# "Moved 3 papers to scanning zone (➋ → ➌)"
```

## User Documentation

### Quick Reference

**View Flow:**
```bash
.\docker-helper.ps1 workflow
```

**Zone Order:**
1. ➊ 📥 Intake - Receive boxes
2. ➋ 🔧 Prep - Unbox and prepare
3. ➌ 📸 Scanning - Digitize
4. ➍ ✅ QC - Quality check
5. ➎ 📤 Output - Final disposition

**Remember:**
- Always move LEFT → RIGHT
- Cannot go backwards
- Cannot skip zones
- Output is the end

### Troubleshooting

**Error: "Cannot move backwards from X to Y"**
- Solution: Use correct forward flow
- Check zone order with workflow CLI

**Error: "Cannot skip zones"**
- Solution: Process through each zone in order
- Intake → Prep → Scanning → QC → Output

**Need to rescan?**
- Only from QC → Scanning
- Use send_for_rescan() method
- This is the only exception

## Integration with Existing Code

All existing functionality preserved:
- Zone capacities unchanged
- Paper/box tracking intact
- Statistics and reporting work
- CLI tools enhanced (not replaced)

New features added:
- Flow validation layer
- Visual indicators
- Workflow status API
- Enhanced error messages

## Future Enhancements

Potential additions:
- Graphical web UI with flow diagram
- Real-time flow animation
- Zone transition alerts
- Flow bottleneck detection
- Automated flow optimization suggestions
