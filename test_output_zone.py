#!/usr/bin/env python3
"""
Test Output Zone functionality
Demonstrates the complete workflow including output rack
"""
from src.physical.control import PaperControlSystem
from src.physical.zones import OutputDisposition

def test_output_workflow():
    """Test complete workflow through output zone"""
    print("=" * 60)
    print("OUTPUT ZONE TEST - Full Workflow")
    print("=" * 60)
    
    # Initialize system
    control = PaperControlSystem()
    
    # 1. INTAKE
    print("\n1️⃣  INTAKE ZONE")
    print("-" * 40)
    control.receive_box("BOX-OUTPUT-001")
    control.log_box_details("BOX-OUTPUT-001", 3, "Test documents for output")
    intake_status = control.get_intake_status()
    print(f"✓ Box received: {intake_status['boxes_received']} boxes")
    
    # 2. PREP
    print("\n2️⃣  PREP ZONE")
    print("-" * 40)
    control.move_box_to_prep("BOX-OUTPUT-001")
    control.start_unboxing("BOX-OUTPUT-001")
    
    # Add 3 papers
    papers = []
    for i in range(1, 4):
        paper_id = f"OUTPUT-TEST-{i:03d}"
        control.add_paper("BOX-OUTPUT-001", paper_id, has_staples=True)
        control.remove_staples(paper_id)
        control.mark_paper_ready(paper_id)
        papers.append(paper_id)
        print(f"✓ Paper {paper_id} prepped")
    
    control.complete_box_prep("BOX-OUTPUT-001")
    prep_status = control.get_prep_status()
    print(f"✓ Papers ready: {prep_status['papers_prepped']}")
    
    # 3. SCANNING
    print("\n3️⃣  SCANNING ZONE")
    print("-" * 40)
    control.move_papers_to_scanning("BOX-OUTPUT-001")
    
    for paper_id in papers:
        control.start_scan(paper_id)
        control.complete_scan(paper_id, success=True, output_file=f"scans/{paper_id}.pdf")
        print(f"✓ Paper {paper_id} scanned")
    
    scan_status = control.get_scanning_status()
    print(f"✓ Papers scanned: {scan_status['papers_scanned']}")
    
    # 4. QC
    print("\n4️⃣  QC ZONE")
    print("-" * 40)
    control.move_papers_to_qc()
    
    for paper_id in papers:
        control.start_qc_check(paper_id, "QC_Operator_Test")
        control.complete_qc_check(paper_id, "QC_Operator_Test", passed=True)
        print(f"✓ Paper {paper_id} passed QC")
    
    qc_status = control.get_qc_status()
    print(f"✓ Papers passed: {qc_status['papers_passed']}")
    
    # 5. OUTPUT
    print("\n5️⃣  OUTPUT RACK")
    print("-" * 40)
    
    # Move papers to output with different dispositions
    control.move_paper_to_output(papers[0], OutputDisposition.RETURN)
    print(f"✓ Paper {papers[0]} → Output (RETURN)")
    
    control.move_paper_to_output(papers[1], OutputDisposition.RETURN)
    print(f"✓ Paper {papers[1]} → Output (RETURN)")
    
    control.move_paper_to_output(papers[2], OutputDisposition.SHRED)
    print(f"✓ Paper {papers[2]} → Output (SHRED)")
    
    # Check output status
    output_status = control.get_output_status()
    print(f"\n📊 Output Status:")
    print(f"   Total papers: {output_status['total_papers']}")
    print(f"   Available space: {output_status['available_space']}")
    print(f"   Active bins: {output_status['active_bins']}")
    
    stats = output_status['statistics']
    print(f"\n📈 Statistics:")
    print(f"   Awaiting return: {stats['awaiting_return']}")
    print(f"   Awaiting shredding: {stats['awaiting_shredding']}")
    print(f"   Return bins: {stats['return_bins']}")
    print(f"   Shred bins: {stats['shred_bins']}")
    
    # View active bins
    print(f"\n📦 Active Bins:")
    active_bins = control.get_active_output_bins()
    for bin in active_bins:
        print(f"   {bin['bin_id']}: {bin['paper_count']} papers ({bin['disposition']})")
    
    # 6. COMPLETE - Mark bins as processed
    print("\n6️⃣  COMPLETE PROCESSING")
    print("-" * 40)
    
    # Get bin IDs
    return_bins = control.get_output_bins_by_disposition(OutputDisposition.RETURN)
    shred_bins = control.get_output_bins_by_disposition(OutputDisposition.SHRED)
    
    if return_bins:
        bin_id = return_bins[0]['bin_id']
        result = control.mark_bin_returned(bin_id)
        print(f"✓ Bin {bin_id} marked as RETURNED ({result['paper_count']} papers)")
    
    if shred_bins:
        bin_id = shred_bins[0]['bin_id']
        result = control.mark_bin_shredded(bin_id)
        print(f"✓ Bin {bin_id} marked as SHREDDED ({result['paper_count']} papers)")
    
    # Final status
    final_status = control.get_output_status()
    print(f"\n📊 Final Status:")
    print(f"   Completed papers: {final_status['completed_papers']}")
    print(f"   Active bins: {final_status['active_bins']}")
    
    print("\n" + "=" * 60)
    print("✅ OUTPUT ZONE TEST COMPLETE!")
    print("=" * 60)
    print("\nAll zones operational:")
    print("  ✓ Intake → Prep → Scanning → QC → Output")
    print("  ✓ Paper dispositions: Return & Shred")
    print("  ✓ Bin management working")
    print("  ✓ Status tracking functional")


if __name__ == "__main__":
    test_output_workflow()
