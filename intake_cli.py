"""
Intake Zone CLI Interface
Simple command-line tool for managing the intake zone
"""
import sys
from datetime import datetime
from src.physical.control import PaperControlSystem


def print_header():
    """Print CLI header"""
    print("\n" + "="*60)
    print("  AI PAPER READER - INTAKE ZONE CONTROL")
    print("  ➊ 📥 INTAKE → ➋ Prep → ➌ Scanning → ➍ QC → ➎ Output")
    print("  Purpose: Move and control paper safely")
    print("="*60 + "\n")


def print_menu():
    """Display main menu"""
    print("\n📥 INTAKE ZONE (➊) - Starting Point")
    print("Available Commands:")
    print("  1. Receive Box - Register new box arrival")
    print("  2. Log Box Details - Record paper count and notes")
    print("  3. View Intake Status - Check zone status")
    print("  4. View Box Info - Get details about specific box")
    print("  5. View Movement History - See all logged activities")
    print("  6. Exit")
    print()


def main():
    """Main CLI loop"""
    control = PaperControlSystem()
    print_header()
    
    while True:
        print_menu()
        choice = input("Enter command (1-6): ").strip()
        
        if choice == '1':
            # Receive box
            box_id = input("Enter Box ID: ").strip()
            if not box_id:
                print("❌ Box ID cannot be empty")
                continue
            
            result = control.receive_box(box_id)
            if result['success']:
                print(f"\n✅ Box {result['box_id']} received successfully!")
                print(f"   Received at: {result['received_at']}")
                print(f"   Status: {result['status']}")
                print(f"   Next step: {result['next_step']}")
            else:
                print(f"\n❌ Error: {result['error']}")
        
        elif choice == '2':
            # Log box details
            box_id = input("Enter Box ID: ").strip()
            try:
                paper_count = int(input("Enter paper count: ").strip())
                notes = input("Enter notes (optional): ").strip()
                
                result = control.log_box_details(box_id, paper_count, notes)
                if result['success']:
                    print(f"\n✅ Box {result['box_id']} logged successfully!")
                    print(f"   Paper count: {result['paper_count']}")
                    print(f"   Status: {result['status']}")
                    print(f"   Ready for processing: {result['ready_for_processing']}")
                else:
                    print(f"\n❌ Error: {result['error']}")
            except ValueError:
                print("\n❌ Invalid paper count. Please enter a number.")
        
        elif choice == '3':
            # View intake status
            status = control.get_intake_status()
            print("\n" + "="*60)
            print(f"INTAKE ZONE STATUS - {status['zone_id']}")
            print("="*60)
            print(f"Total boxes: {status['total_boxes']}/{status['capacity']}")
            print(f"Available space: {status['available_space']}")
            print(f"Received (not logged): {status['received_count']}")
            print(f"Logged (ready): {status['logged_count']}")
            
            if status['logged_boxes']:
                print("\nLogged boxes ready for processing:")
                for box in status['logged_boxes']:
                    print(f"  - {box['box_id']}: {box['paper_count']} papers")
        
        elif choice == '4':
            # View box info
            box_id = input("Enter Box ID: ").strip()
            info = control.get_box_info(box_id)
            
            if info:
                print("\n" + "="*60)
                print(f"BOX INFORMATION - {info['box_id']}")
                print("="*60)
                print(f"Status: {info['status']}")
                print(f"Current zone: {info['current_zone']}")
                print(f"Received at: {info['received_at']}")
                print(f"Paper count: {info['paper_count']}")
                print(f"Notes: {info['notes']}")
            else:
                print(f"\n❌ Box {box_id} not found")
        
        elif choice == '5':
            # View movement history
            box_id = input("Enter Box ID (press Enter for all): ").strip()
            box_id = box_id if box_id else None
            
            history = control.get_movement_history(box_id)
            
            if history:
                print("\n" + "="*60)
                print("MOVEMENT HISTORY")
                print("="*60)
                for entry in history:
                    print(f"\n[{entry['timestamp']}]")
                    print(f"  Action: {entry['action']}")
                    print(f"  Box ID: {entry['box_id']}")
                    if 'paper_count' in entry:
                        print(f"  Paper count: {entry['paper_count']}")
                    print(f"  Status: {entry['status']}")
            else:
                print("\nNo movement history found")
        
        elif choice == '6':
            print("\nExiting intake zone control. Goodbye!\n")
            sys.exit(0)
        
        else:
            print("\n❌ Invalid choice. Please enter 1-6.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting. Goodbye!\n")
        sys.exit(0)
