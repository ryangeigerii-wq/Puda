"""
Prep Zone CLI Interface
Command-line tool for managing the prep zone (unboxing, sorting, removing staples)
"""
import sys
from src.physical.control import PaperControlSystem


def print_header():
    """Print CLI header"""
    print("\n" + "="*60)
    print("  AI PAPER READER - PREP ZONE CONTROL")
    print("  Purpose: Unbox, sort, and remove staples")
    print("="*60 + "\n")


def print_menu():
    """Display main menu"""
    print("\nAvailable Commands:")
    print("  1. Move Box to Prep - Transfer box from intake")
    print("  2. Start Unboxing - Begin unboxing process")
    print("  3. Add Paper - Add individual paper from box")
    print("  4. Remove Staples - Remove staples from paper")
    print("  5. Mark Paper Ready - Mark paper ready for scanning")
    print("  6. Complete Box Prep - Finish entire box")
    print("  7. View Prep Status - Check zone status")
    print("  8. View Paper Info - Get paper details")
    print("  9. Back to Main Menu")
    print()


def prep_zone_menu(control: PaperControlSystem):
    """Prep zone management interface"""
    print_header()
    
    while True:
        print_menu()
        choice = input("Enter command (1-9): ").strip()
        
        if choice == '1':
            # Move box to prep
            box_id = input("Enter Box ID: ").strip()
            if not box_id:
                print("❌ Box ID cannot be empty")
                continue
            
            result = control.move_box_to_prep(box_id)
            if result['success']:
                print(f"\n✅ Box {result['box_id']} moved to prep zone!")
                print(f"   Current zone: {result['current_zone']}")
                print(f"   Status: {result['status']}")
                print(f"   Next step: {result['next_step']}")
            else:
                print(f"\n❌ Error: {result['error']}")
        
        elif choice == '2':
            # Start unboxing
            box_id = input("Enter Box ID: ").strip()
            result = control.start_unboxing(box_id)
            
            if result['success']:
                print(f"\n✅ Started unboxing box {result['box_id']}")
                print(f"   Status: {result['status']}")
                print(f"   Expected papers: {result['expected_papers']}")
            else:
                print(f"\n❌ Error: {result['error']}")
        
        elif choice == '3':
            # Add paper
            box_id = input("Enter Box ID: ").strip()
            paper_id = input("Enter Paper ID: ").strip()
            
            has_staples_input = input("Has staples? (y/n, default=y): ").strip().lower()
            has_staples = has_staples_input != 'n'
            
            try:
                pages = int(input("Number of pages (default=1): ").strip() or "1")
            except ValueError:
                pages = 1
            
            result = control.add_paper(box_id, paper_id, has_staples, pages)
            
            if result['success']:
                print(f"\n✅ Paper {result['paper_id']} added!")
                print(f"   Box ID: {result['box_id']}")
                print(f"   Has staples: {result['has_staples']}")
                print(f"   Status: {result['status']}")
            else:
                print(f"\n❌ Error: {result['error']}")
        
        elif choice == '4':
            # Remove staples
            paper_id = input("Enter Paper ID: ").strip()
            result = control.remove_staples(paper_id)
            
            if result['success']:
                print(f"\n✅ Staples removed from paper {result['paper_id']}")
                print(f"   Has staples: {result['has_staples']}")
                print(f"   Status: {result['status']}")
            else:
                print(f"\n❌ Error: {result['error']}")
        
        elif choice == '5':
            # Mark paper ready
            paper_id = input("Enter Paper ID: ").strip()
            result = control.mark_paper_ready(paper_id)
            
            if result['success']:
                print(f"\n✅ Paper {result['paper_id']} ready for scanning!")
                print(f"   Status: {result['status']}")
                print(f"   Ready: {result['ready_for_scanning']}")
            else:
                print(f"\n❌ Error: {result['error']}")
        
        elif choice == '6':
            # Complete box prep
            box_id = input("Enter Box ID: ").strip()
            result = control.complete_box_prep(box_id)
            
            if result['success']:
                print(f"\n✅ Box {result['box_id']} prep completed!")
                print(f"   Status: {result['status']}")
                print(f"   Next step: {result['next_step']}")
            else:
                print(f"\n❌ Error: {result['error']}")
        
        elif choice == '7':
            # View prep status
            status = control.get_prep_status()
            print("\n" + "="*60)
            print(f"PREP ZONE STATUS - {status['zone_id']}")
            print("="*60)
            print(f"Total boxes: {status['total_boxes']}/{status['capacity']}")
            print(f"Available space: {status['available_space']}")
            print(f"Total papers: {status['total_papers']}")
            print(f"Papers with staples: {status['papers_with_staples']}")
            print(f"Papers ready: {status['papers_ready']}")
            print(f"Boxes in prep: {status['boxes_in_prep']}")
            print(f"Boxes complete: {status['boxes_complete']}")
        
        elif choice == '8':
            # View paper info
            paper_id = input("Enter Paper ID: ").strip()
            info = control.get_paper_info(paper_id)
            
            if info:
                print("\n" + "="*60)
                print(f"PAPER INFORMATION - {info['paper_id']}")
                print("="*60)
                print(f"Box ID: {info['box_id']}")
                print(f"Status: {info['status']}")
                print(f"Current zone: {info['current_zone']}")
                print(f"Has staples: {info['has_staples']}")
                print(f"Pages: {info['pages']}")
                print(f"Notes: {info['notes']}")
            else:
                print(f"\n❌ Paper {paper_id} not found")
        
        elif choice == '9':
            return
        
        else:
            print("\n❌ Invalid choice. Please enter 1-9.")


def main():
    """Main CLI entry point"""
    control = PaperControlSystem()
    
    while True:
        print("\n" + "="*60)
        print("  AI PAPER READER - PHYSICAL CONTROL SYSTEM")
        print("="*60)
        print("\n1. Intake Zone")
        print("2. Prep Zone")
        print("3. Exit")
        
        choice = input("\nSelect zone (1-3): ").strip()
        
        if choice == '1':
            from intake_cli import main as intake_main
            # Show intake zone (import and delegate)
            print("\nIntake zone - use intake_cli.py")
        elif choice == '2':
            prep_zone_menu(control)
        elif choice == '3':
            print("\nExiting. Goodbye!\n")
            sys.exit(0)
        else:
            print("\n❌ Invalid choice. Please enter 1-3.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting. Goodbye!\n")
        sys.exit(0)
