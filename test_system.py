"""
Simple test script to verify the system is working
Run this in Docker: docker-compose exec puda-app python test_system.py
"""
from src.physical.control import PaperControlSystem
from datetime import datetime

def test_full_workflow():
    """Test complete workflow from intake to scanning"""
    print("\n" + "="*60)
    print("AI Paper Reader - System Test")
    print("="*60 + "\n")
    
    control = PaperControlSystem()
    
    # Test 1: Intake Zone
    print("📥 Test 1: Intake Zone")
    box_id = f"TEST-BOX-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    result = control.receive_box(box_id)
    assert result['success'], "Failed to receive box"
    print(f"  ✅ Box received: {box_id}")
    
    result = control.log_box_details(box_id, 10, "Test documents")
    assert result['success'], "Failed to log box"
    print(f"  ✅ Box logged with 10 papers")
    
    status = control.get_intake_status()
    print(f"  ℹ️  Intake zone: {status['total_boxes']} boxes")
    
    # Test 2: Prep Zone
    print("\n🔧 Test 2: Prep Zone")
    
    result = control.move_box_to_prep(box_id)
    assert result['success'], "Failed to move to prep"
    print(f"  ✅ Box moved to prep zone")
    
    result = control.start_unboxing(box_id)
    assert result['success'], "Failed to start unboxing"
    print(f"  ✅ Unboxing started")
    
    # Add 3 test papers
    paper_ids = []
    for i in range(1, 4):
        paper_id = f"TEST-PAPER-{i:03d}"
        result = control.add_paper(box_id, paper_id, has_staples=True, pages=2)
        assert result['success'], f"Failed to add paper {paper_id}"
        paper_ids.append(paper_id)
        
        result = control.remove_staples(paper_id)
        assert result['success'], f"Failed to remove staples from {paper_id}"
        
        result = control.mark_paper_ready(paper_id)
        assert result['success'], f"Failed to mark {paper_id} ready"
    
    print(f"  ✅ Added and prepared 3 papers")
    
    result = control.complete_box_prep(box_id)
    assert result['success'], "Failed to complete box prep"
    print(f"  ✅ Box prep completed")
    
    status = control.get_prep_status()
    print(f"  ℹ️  Prep zone: {status['total_papers']} papers")
    
    # Test 3: Scanning Zone
    print("\n📸 Test 3: Scanning Zone")
    
    result = control.move_papers_to_scanning(box_id)
    assert result['success'], "Failed to move to scanning"
    print(f"  ✅ {result['papers_moved']} papers moved to scanning")
    
    status = control.get_scanning_status()
    print(f"  ℹ️  Scanning zone: {status['papers_in_queue']} in queue")
    print(f"  ℹ️  Available stations: {status['available_stations']}/{status['total_stations']}")
    
    # Scan the papers
    for paper_id in paper_ids:
        result = control.start_scan(paper_id)
        assert result['success'], f"Failed to start scan for {paper_id}"
        
        result = control.complete_scan(
            paper_id=paper_id,
            success=True,
            output_file=f"/app/data/scans/{paper_id}.pdf"
        )
        assert result['success'], f"Failed to complete scan for {paper_id}"
    
    print(f"  ✅ All papers scanned successfully")
    
    status = control.get_scanning_status()
    print(f"  ℹ️  Papers scanned: {status['papers_scanned']}")
    print(f"  ℹ️  Total scanned today: {status['papers_scanned_today']}")
    
    # Summary
    print("\n" + "="*60)
    print("✅ All Tests Passed!")
    print("="*60)
    print(f"\nWorkflow Summary:")
    print(f"  • Box ID: {box_id}")
    print(f"  • Papers processed: {len(paper_ids)}")
    print(f"  • Zones traversed: Intake → Prep → Scanning")
    print(f"  • Status: Complete")
    print("\n🎉 System is working correctly!\n")

if __name__ == "__main__":
    try:
        test_full_workflow()
    except AssertionError as e:
        print(f"\n❌ Test Failed: {e}\n")
        exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}\n")
        import traceback
        traceback.print_exc()
        exit(1)
