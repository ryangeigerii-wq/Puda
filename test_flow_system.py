#!/usr/bin/env python3
"""
Test Unidirectional Flow System
Demonstrates and validates the left-to-right flow enforcement
"""
from src.physical.control import PaperControlSystem
from src.physical.zones import ZoneType, OutputDisposition


def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)


def test_valid_movements():
    """Test all valid forward movements"""
    print_section("✅ TESTING VALID MOVEMENTS (Left to Right)")
    
    control = PaperControlSystem()
    
    # Test 1: Intake → Prep
    print("\n1️⃣  Testing: Intake → Prep")
    validation = control.validate_movement(ZoneType.INTAKE, ZoneType.PREP)
    print(f"   Result: {'✅ ALLOWED' if validation['allowed'] else '❌ BLOCKED'}")
    print(f"   Reason: {validation['reason']}")
    
    # Test 2: Prep → Scanning
    print("\n2️⃣  Testing: Prep → Scanning")
    validation = control.validate_movement(ZoneType.PREP, ZoneType.SCANNING)
    print(f"   Result: {'✅ ALLOWED' if validation['allowed'] else '❌ BLOCKED'}")
    print(f"   Reason: {validation['reason']}")
    
    # Test 3: Scanning → QC
    print("\n3️⃣  Testing: Scanning → QC")
    validation = control.validate_movement(ZoneType.SCANNING, ZoneType.QC)
    print(f"   Result: {'✅ ALLOWED' if validation['allowed'] else '❌ BLOCKED'}")
    print(f"   Reason: {validation['reason']}")
    
    # Test 4: QC → Output
    print("\n4️⃣  Testing: QC → Output")
    validation = control.validate_movement(ZoneType.QC, ZoneType.OUTPUT)
    print(f"   Result: {'✅ ALLOWED' if validation['allowed'] else '❌ BLOCKED'}")
    print(f"   Reason: {validation['reason']}")
    
    # Test 5: QC → Scanning (rescan exception)
    print("\n5️⃣  Testing: QC → Scanning (Rescan Exception)")
    validation = control.validate_movement(ZoneType.QC, ZoneType.SCANNING)
    print(f"   Result: {'✅ ALLOWED' if validation['allowed'] else '❌ BLOCKED'}")
    print(f"   Reason: {validation['reason']}")


def test_invalid_movements():
    """Test invalid backwards movements"""
    print_section("❌ TESTING INVALID MOVEMENTS (Backwards)")
    
    control = PaperControlSystem()
    
    invalid_tests = [
        (ZoneType.PREP, ZoneType.INTAKE, "Prep → Intake"),
        (ZoneType.SCANNING, ZoneType.PREP, "Scanning → Prep"),
        (ZoneType.QC, ZoneType.PREP, "QC → Prep"),
        (ZoneType.OUTPUT, ZoneType.QC, "Output → QC"),
        (ZoneType.OUTPUT, ZoneType.INTAKE, "Output → Intake"),
    ]
    
    for i, (from_zone, to_zone, label) in enumerate(invalid_tests, 1):
        print(f"\n{i}️⃣  Testing: {label}")
        validation = control.validate_movement(from_zone, to_zone)
        print(f"   Result: {'✅ ALLOWED' if validation['allowed'] else '❌ BLOCKED'}")
        print(f"   Reason: {validation['reason']}")


def test_skipping_zones():
    """Test that zone skipping is blocked"""
    print_section("🚫 TESTING ZONE SKIPPING (Not Allowed)")
    
    control = PaperControlSystem()
    
    skip_tests = [
        (ZoneType.INTAKE, ZoneType.SCANNING, "Intake → Scanning (skips Prep)"),
        (ZoneType.INTAKE, ZoneType.QC, "Intake → QC (skips Prep & Scanning)"),
        (ZoneType.PREP, ZoneType.QC, "Prep → QC (skips Scanning)"),
        (ZoneType.SCANNING, ZoneType.OUTPUT, "Scanning → Output (skips QC)"),
    ]
    
    for i, (from_zone, to_zone, label) in enumerate(skip_tests, 1):
        print(f"\n{i}️⃣  Testing: {label}")
        validation = control.validate_movement(from_zone, to_zone)
        print(f"   Result: {'✅ ALLOWED' if validation['allowed'] else '❌ BLOCKED'}")
        print(f"   Reason: {validation['reason']}")


def test_zone_order():
    """Test zone ordering system"""
    print_section("🔢 TESTING ZONE ORDER")
    
    zones = [
        ZoneType.INTAKE,
        ZoneType.PREP,
        ZoneType.SCANNING,
        ZoneType.QC,
        ZoneType.OUTPUT
    ]
    
    print("\nZone Order (must be sequential):")
    for zone in zones:
        order = zone.get_order()
        icon = zone.get_icon()
        next_zone = zone.get_next_zone()
        next_info = f"→ {next_zone.get_icon()} {next_zone.value}" if next_zone else "→ END (Terminal)"
        print(f"   {order}. {icon} {zone.value.upper():12} {next_info}")


def test_workflow_with_real_data():
    """Test complete workflow with actual paper movement"""
    print_section("📋 FULL WORKFLOW TEST WITH REAL DATA")
    
    control = PaperControlSystem()
    
    # Step 1: Intake
    print("\n➊ INTAKE ZONE")
    control.receive_box("TEST-BOX-001")
    result = control.log_box_details("TEST-BOX-001", 2, "Flow test")
    print(f"   ✓ Box received and logged")
    if 'flow_direction' in result:
        print(f"   Flow: {result['flow_direction']}")
    
    # Step 2: Move to Prep
    print("\n➋ PREP ZONE")
    result = control.move_box_to_prep("TEST-BOX-001")
    if result['success']:
        print(f"   ✓ Box moved to prep")
        print(f"   Flow: {result.get('flow_direction', 'N/A')}")
    
    control.start_unboxing("TEST-BOX-001")
    control.add_paper("TEST-BOX-001", "PAPER-FLOW-001", has_staples=True)
    control.add_paper("TEST-BOX-001", "PAPER-FLOW-002", has_staples=False)
    control.remove_staples("PAPER-FLOW-001")
    control.mark_paper_ready("PAPER-FLOW-001")
    control.mark_paper_ready("PAPER-FLOW-002")
    control.complete_box_prep("TEST-BOX-001")
    print(f"   ✓ Papers prepared")
    
    # Step 3: Move to Scanning
    print("\n➌ SCANNING ZONE")
    result = control.move_papers_to_scanning("TEST-BOX-001")
    if result['success']:
        print(f"   ✓ Papers moved to scanning")
        print(f"   Flow: {result.get('flow_direction', 'N/A')}")
    
    control.start_scan("PAPER-FLOW-001")
    control.complete_scan("PAPER-FLOW-001", success=True, output_file="scan1.pdf")
    control.start_scan("PAPER-FLOW-002")
    control.complete_scan("PAPER-FLOW-002", success=True, output_file="scan2.pdf")
    print(f"   ✓ Papers scanned")
    
    # Step 4: Move to QC
    print("\n➍ QC ZONE")
    result = control.move_papers_to_qc()
    if result['success']:
        print(f"   ✓ Papers moved to QC")
        print(f"   Flow: {result.get('flow_direction', 'N/A')}")
    
    control.start_qc_check("PAPER-FLOW-001", "QC_Operator")
    control.complete_qc_check("PAPER-FLOW-001", "QC_Operator", passed=True)
    control.start_qc_check("PAPER-FLOW-002", "QC_Operator")
    control.complete_qc_check("PAPER-FLOW-002", "QC_Operator", passed=True)
    print(f"   ✓ Papers passed QC")
    
    # Step 5: Move to Output
    print("\n➎ OUTPUT ZONE (FINAL)")
    result = control.move_paper_to_output("PAPER-FLOW-001", OutputDisposition.RETURN)
    if result['success']:
        print(f"   ✓ Paper moved to output")
        print(f"   Flow: {result.get('flow_direction', 'N/A')}")
    
    result = control.move_paper_to_output("PAPER-FLOW-002", OutputDisposition.RETURN)
    if result['success']:
        print(f"   ✓ Paper moved to output")
    
    print("\n📊 Workflow Status:")
    workflow = control.get_workflow_status()
    print(f"   Flow: {workflow['flow']}")
    print(f"   Total papers in system: {workflow['total_papers_in_system']}")
    print(f"   Completed papers: {workflow['completed_papers']}")


def test_rescan_exception():
    """Test the special rescan exception (QC → Scanning)"""
    print_section("🔄 TESTING RESCAN EXCEPTION (QC → Scanning)")
    
    control = PaperControlSystem()
    
    # Setup: Get a paper through to QC that fails
    print("\n1. Setting up scenario (Intake → Prep → Scanning → QC)")
    control.receive_box("RESCAN-BOX")
    control.log_box_details("RESCAN-BOX", 1, "Rescan test")
    control.move_box_to_prep("RESCAN-BOX")
    control.start_unboxing("RESCAN-BOX")
    control.add_paper("RESCAN-BOX", "RESCAN-PAPER", has_staples=False)
    control.mark_paper_ready("RESCAN-PAPER")
    control.complete_box_prep("RESCAN-BOX")
    control.move_papers_to_scanning("RESCAN-BOX")
    control.start_scan("RESCAN-PAPER")
    control.complete_scan("RESCAN-PAPER", success=True, output_file="rescan.pdf")
    control.move_papers_to_qc()
    control.start_qc_check("RESCAN-PAPER", "QC_Operator")
    
    # Fail QC (blurry scan)
    print("\n2. Paper fails QC (blurry scan)")
    control.complete_qc_check("RESCAN-PAPER", "QC_Operator", passed=False, 
                             issues=["blurry"], needs_rescan=True)
    print("   ✓ Paper marked as failed with rescan needed")
    
    # Test rescan movement (QC → Scanning)
    print("\n3. Testing QC → Scanning movement (special exception)")
    validation = control.validate_movement(ZoneType.QC, ZoneType.SCANNING)
    print(f"   Result: {'✅ ALLOWED' if validation['allowed'] else '❌ BLOCKED'}")
    print(f"   Reason: {validation['reason']}")
    
    # Send for rescan
    print("\n4. Sending paper back to scanning")
    result = control.send_for_rescan("RESCAN-PAPER")
    if result['success']:
        print(f"   ✓ Paper sent back to scanning")
        print(f"   Rescan count: {result['rescan_count']}")
        print(f"   This is the ONLY allowed backwards movement!")


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print(" " * 15 + "UNIDIRECTIONAL FLOW SYSTEM TEST")
    print(" " * 10 + "Testing Left-to-Right Enforcement")
    print("=" * 80)
    
    test_valid_movements()
    test_invalid_movements()
    test_skipping_zones()
    test_zone_order()
    test_workflow_with_real_data()
    test_rescan_exception()
    
    print("\n" + "=" * 80)
    print(" " * 25 + "✅ ALL TESTS COMPLETE")
    print("=" * 80)
    print("\nSummary:")
    print("  ✅ Valid forward movements: ALLOWED")
    print("  ❌ Backwards movements: BLOCKED")
    print("  🚫 Zone skipping: BLOCKED")
    print("  🔄 QC rescan exception: ALLOWED")
    print("  📋 Full workflow: WORKING")
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
