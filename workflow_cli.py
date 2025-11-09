#!/usr/bin/env python3
"""
Workflow Visualizer CLI - Physical Paper Management System
Purpose: Show unidirectional left-to-right flow of entire system
"""
import sys
from src.physical.control import PaperControlSystem
from src.physical.zones import ZoneType


def print_header():
    """Print the visual header"""
    print("\n" + "=" * 80)
    print(" " * 20 + "📋 PAPER PROCESSING WORKFLOW")
    print(" " * 15 + "Left-to-Right Unidirectional Flow")
    print("=" * 80)


def print_flow_diagram():
    """Print the flow diagram with icons"""
    print("\n┌─────────────────────────────────────────────────────────────────────────────┐")
    print("│  UNIDIRECTIONAL FLOW (No Backwards Movement)                                │")
    print("├─────────────────────────────────────────────────────────────────────────────┤")
    print("│                                                                              │")
    print("│   ➊ 📥      →      ➋ 🔧      →      ➌ 📸      →      ➍ ✅      →      ➎ 📤    │")
    print("│   INTAKE          PREP         SCANNING         QC           OUTPUT        │")
    print("│   Receive         Unbox        Digitize        Check         Final         │")
    print("│   Boxes           Papers       Documents       Quality       Disposition   │")
    print("│                                                   ↓                         │")
    print("│                                              Rescan Only                    │")
    print("│                                              (QC → Scan)                    │")
    print("│                                                                              │")
    print("└─────────────────────────────────────────────────────────────────────────────┘")


def print_zone_status(control: PaperControlSystem):
    """Print detailed status of each zone"""
    print("\n" + "─" * 80)
    print("ZONE STATUS (Left to Right)")
    print("─" * 80)
    
    workflow = control.get_workflow_status()
    
    for zone in workflow['zones']:
        icon = zone['icon']
        name = zone['name']
        order = zone['order']
        capacity = zone['capacity']
        status = zone['status']
        
        # Status indicator
        status_indicator = "🟢" if status == "active" else "⚪"
        
        print(f"\n{status_indicator} Zone {order}: {icon} {name.upper()}")
        print(f"   Capacity: {capacity}")
        
        if 'papers' in zone:
            print(f"   Papers: {zone['papers']}")
        if 'boxes' in zone:
            print(f"   Boxes: {zone['boxes']}")
        
        # Show next zone
        zone_type = ZoneType[name.upper()]
        next_zone = zone_type.get_next_zone()
        if next_zone:
            print(f"   Next Zone: {next_zone.get_icon()} {next_zone.value.title()}")
        else:
            print(f"   Next Zone: ✋ FINAL ZONE - No further movement")


def print_summary(control: PaperControlSystem):
    """Print system summary"""
    workflow = control.get_workflow_status()
    
    print("\n" + "─" * 80)
    print("SYSTEM SUMMARY")
    print("─" * 80)
    print(f"📊 Total Papers in System: {workflow['total_papers_in_system']}")
    print(f"✅ Completed Papers: {workflow['completed_papers']}")
    print(f"📈 Active Zones: {sum(1 for z in workflow['zones'] if z['status'] == 'active')}/5")
    
    print("\n🔒 Flow Rules:")
    print("   • Movement is ALWAYS left to right")
    print("   • No backwards movement (except QC rescan)")
    print("   • Papers cannot skip zones")
    print("   • Output is the final destination")


def test_flow_validation(control: PaperControlSystem):
    """Test and display flow validation"""
    print("\n" + "─" * 80)
    print("FLOW VALIDATION EXAMPLES")
    print("─" * 80)
    
    # Valid movements
    valid_tests = [
        (ZoneType.INTAKE, ZoneType.PREP, "✅ VALID"),
        (ZoneType.PREP, ZoneType.SCANNING, "✅ VALID"),
        (ZoneType.SCANNING, ZoneType.QC, "✅ VALID"),
        (ZoneType.QC, ZoneType.OUTPUT, "✅ VALID"),
        (ZoneType.QC, ZoneType.SCANNING, "✅ VALID (Rescan Exception)")
    ]
    
    print("\n✅ Allowed Movements:")
    for from_zone, to_zone, label in valid_tests:
        validation = control.validate_movement(from_zone, to_zone)
        print(f"   {from_zone.get_icon()} {from_zone.value.title()} → {to_zone.get_icon()} {to_zone.value.title()}")
        print(f"      {label}: {validation['reason']}")
    
    # Invalid movements
    invalid_tests = [
        (ZoneType.PREP, ZoneType.INTAKE, "❌ BLOCKED"),
        (ZoneType.SCANNING, ZoneType.PREP, "❌ BLOCKED"),
        (ZoneType.QC, ZoneType.PREP, "❌ BLOCKED"),
        (ZoneType.OUTPUT, ZoneType.QC, "❌ BLOCKED"),
        (ZoneType.INTAKE, ZoneType.SCANNING, "❌ BLOCKED (Skips Zone)")
    ]
    
    print("\n❌ Blocked Movements:")
    for from_zone, to_zone, label in invalid_tests:
        validation = control.validate_movement(from_zone, to_zone)
        print(f"   {from_zone.get_icon()} {from_zone.value.title()} → {to_zone.get_icon()} {to_zone.value.title()}")
        print(f"      {label}: {validation['reason']}")


def display_menu():
    """Display menu options"""
    print("\n" + "=" * 80)
    print("WORKFLOW VISUALIZER MENU")
    print("=" * 80)
    print("1. View Flow Diagram")
    print("2. View Zone Status")
    print("3. View System Summary")
    print("4. Test Flow Validation")
    print("5. View Complete Report (All Above)")
    print("6. Exit")
    print("=" * 80)


def show_complete_report(control: PaperControlSystem):
    """Show all information"""
    print_header()
    print_flow_diagram()
    print_zone_status(control)
    print_summary(control)
    test_flow_validation(control)


def main():
    """Main CLI loop"""
    print_header()
    print("\nInitializing Paper Control System...")
    control = PaperControlSystem()
    
    # Show initial diagram
    print_flow_diagram()
    
    while True:
        display_menu()
        choice = input("\nSelect option (1-6): ").strip()
        
        if choice == '1':
            print_flow_diagram()
        elif choice == '2':
            print_zone_status(control)
        elif choice == '3':
            print_summary(control)
        elif choice == '4':
            test_flow_validation(control)
        elif choice == '5':
            show_complete_report(control)
        elif choice == '6':
            print("\n✅ Workflow Visualizer closed. Flow remains: Intake → Prep → Scanning → QC → Output")
            sys.exit(0)
        else:
            print("\n✗ Invalid option. Please select 1-6.")
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()
