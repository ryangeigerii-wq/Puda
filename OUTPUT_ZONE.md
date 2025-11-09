# Output Rack Zone - Documentation

## Overview
The Output Rack is the final zone in the physical paper processing workflow. It manages processed papers awaiting return to customers, shredding, or archiving.

## Purpose
- Organize processed papers by disposition
- Track papers awaiting return or shredding
- Manage bins for efficient batch processing
- Maintain completion records

## Features

### Bin Management
- **Automatic bin creation** based on disposition type
- **Capacity tracking** (100 papers per bin)
- **Full bin detection** with auto-creation of new bins
- **Bin status tracking** (active vs. processed)

### Paper Dispositions
1. **RETURN**: Papers to be returned to customer
2. **SHRED**: Papers to be securely destroyed
3. **ARCHIVE**: Papers to be kept for long-term storage

### Paper Status Flow
```
QC_PASSED → PROCESSED → AWAITING_RETURN/AWAITING_SHREDDING → RETURNED/SHREDDED
```

## Capacity
- **Total capacity**: 500 papers
- **Bin capacity**: 100 papers per bin
- **Bins**: Unlimited (auto-created as needed)

## Data Model

### OutputBin
```python
@dataclass
class OutputBin:
    bin_id: str                    # e.g., "BIN-RETURN-001"
    disposition: OutputDisposition  # RETURN, SHRED, ARCHIVE
    papers: List[Paper]
    created_at: datetime
    processed_at: Optional[datetime]
    capacity: int = 100
```

### OutputRack
```python
class OutputRack:
    zone_id: str = "OUTPUT-001"
    zone_type: ZoneType = ZoneType.OUTPUT
    capacity: int = 500
    bins: List[OutputBin]
    papers: List[Paper]
    completed_papers: List[Paper]
```

## Operations

### 1. Receive Processed Paper
```python
control.move_paper_to_output(paper_id, OutputDisposition.RETURN)
```
- Moves paper from QC zone to output rack
- Assigns to appropriate bin (creates new if needed)
- Updates paper status

### 2. Mark Bin Returned
```python
control.mark_bin_returned(bin_id)
```
- Marks all papers in bin as RETURNED
- Updates bin processed timestamp
- Moves papers to completed list

### 3. Mark Bin Shredded
```python
control.mark_bin_shredded(bin_id)
```
- Marks all papers in bin as SHREDDED
- Updates bin processed timestamp
- Moves papers to completed list

## CLI Usage

### Access Output CLI
```powershell
.\docker-helper.ps1 output
```

### Menu Options
1. View Output Status - Current capacity and statistics
2. Move Paper to Output - Transfer from QC with disposition
3. View Active Bins - See unprocessed bins
4. View Bins by Disposition - Filter by return/shred/archive
5. Mark Bin as Returned - Complete return bin
6. Mark Bin as Shredded - Complete shred bin
7. View Papers Awaiting Return - List all return papers
8. View Papers Awaiting Shredding - List all shred papers

## Workflow Example

### Typical Flow
1. Paper passes QC inspection
2. Move to output rack with disposition
3. Paper added to appropriate bin (return/shred)
4. Bin fills up with similar papers
5. Bin is processed (returned or shredded)
6. Papers marked as completed

### Code Example
```python
from src.physical.control import PaperControlSystem
from src.physical.zones import OutputDisposition

control = PaperControlSystem()

# Paper passed QC
paper_id = "PAPER-001"

# Move to output for return
control.move_paper_to_output(paper_id, OutputDisposition.RETURN)

# Check status
status = control.get_output_status()
print(f"Papers awaiting return: {status['statistics']['awaiting_return']}")

# Get return bins
return_bins = control.get_output_bins_by_disposition(OutputDisposition.RETURN)

# When ready, mark bin as returned
control.mark_bin_returned(return_bins[0]['bin_id'])
```

## Statistics & Reporting

### Available Metrics
- Total papers in output
- Papers awaiting return
- Papers awaiting shredding
- Completed papers count
- Total bins
- Active bins (not yet processed)
- Bins by disposition type

### Status Output
```python
{
    'zone_id': 'OUTPUT-001',
    'zone_type': 'output',
    'total_papers': 15,
    'completed_papers': 10,
    'capacity': 500,
    'available_space': 485,
    'active_bins': 2,
    'statistics': {
        'total_papers': 15,
        'awaiting_return': 10,
        'awaiting_shredding': 5,
        'completed': 10,
        'total_bins': 3,
        'active_bins': 2,
        'return_bins': 2,
        'shred_bins': 1,
        'archive_bins': 0
    }
}
```

## Integration Points

### Input (from QC Zone)
- Receives papers that have passed QC
- Papers must be in `passed_papers` list in QC zone

### Output (final destination)
- RETURN: Papers physically returned to customer
- SHRED: Papers sent to secure shredding
- ARCHIVE: Papers stored for long-term retention

## Best Practices

1. **Disposition Assignment**: Set correct disposition immediately when moving from QC
2. **Bin Monitoring**: Check active bins regularly to avoid overflow
3. **Batch Processing**: Wait for bins to fill before processing for efficiency
4. **Verification**: Confirm paper counts before marking bins as complete
5. **Tracking**: Keep records of returned/shredded bin IDs for audit trail

## Error Handling

### Common Issues
- **Output rack at capacity**: Wait for bins to be processed or increase capacity
- **Paper not found**: Ensure paper is in QC passed_papers list
- **Bin not found**: Verify bin_id is correct and active
- **Wrong disposition**: Can only mark return bins as returned, shred bins as shredded

### Solutions
- Check capacity before moving papers
- Verify QC status before output operations
- Process completed bins regularly
- Use status commands to verify bin states

## Testing

Run the test suite:
```bash
python test_output_zone.py
```

This tests:
- Complete workflow (Intake → Prep → Scanning → QC → Output)
- Multiple dispositions (Return & Shred)
- Bin creation and management
- Status tracking
- Completion marking

## Future Enhancements

Potential additions:
- Archive disposition implementation
- Bin priority handling
- Scheduled bin processing
- Customer notification integration
- Shredding certificate generation
- Audit log export
- Bin barcode integration
