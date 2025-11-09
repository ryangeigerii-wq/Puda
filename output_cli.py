#!/usr/bin/env python3
"""
Output Rack CLI - Physical Paper Management System
Purpose: Manage processed papers awaiting return, shredding, or archiving
"""
import sys
from src.physical.control import PaperControlSystem
from src.physical.zones import OutputDisposition


def display_menu():
    """Display main menu options"""
    print("\n" + "=" * 60)
    print("OUTPUT RACK - Processed Paper Management")
    print("=" * 60)
    print("1. View Output Status")
    print("2. Move Paper to Output (from QC)")
    print("3. View Active Bins")
    print("4. View Bins by Disposition")
    print("5. Mark Bin as Returned")
    print("6. Mark Bin as Shredded")
    print("7. View Papers Awaiting Return")
    print("8. View Papers Awaiting Shredding")
    print("9. Exit")
    print("=" * 60)


def view_status(control_system: PaperControlSystem):
    """Display current output rack status"""
    print("\n--- Output Rack Status ---")
    status = control_system.get_output_status()
    
    print(f"Zone ID: {status['zone_id']}")
    print(f"Total Papers: {status['total_papers']}")
    print(f"Completed Papers: {status['completed_papers']}")
    print(f"Capacity: {status['capacity']}")
    print(f"Available Space: {status['available_space']}")
    print(f"Active Bins: {status['active_bins']}")
    
    print("\n--- Statistics ---")
    stats = status['statistics']
    print(f"Awaiting Return: {stats['awaiting_return']}")
    print(f"Awaiting Shredding: {stats['awaiting_shredding']}")
    print(f"Total Bins: {stats['total_bins']}")
    print(f"  - Return Bins: {stats['return_bins']}")
    print(f"  - Shred Bins: {stats['shred_bins']}")
    print(f"  - Archive Bins: {stats['archive_bins']}")


def move_paper_to_output(control_system: PaperControlSystem):
    """Move a paper from QC to output rack"""
    print("\n--- Move Paper to Output ---")
    
    # Show available papers in QC
    qc_status = control_system.get_qc_status()
    if qc_status['papers_passed'] == 0:
        print("No papers available in QC passed papers!")
        return
    
    print(f"Papers available: {qc_status['papers_passed']}")
    
    paper_id = input("Enter Paper ID: ").strip()
    if not paper_id:
        print("Paper ID required!")
        return
    
    print("\nDisposition Options:")
    print("1. Return to Customer")
    print("2. Shred")
    print("3. Archive")
    
    disp_choice = input("Select disposition (1-3): ").strip()
    
    disposition_map = {
        '1': OutputDisposition.RETURN,
        '2': OutputDisposition.SHRED,
        '3': OutputDisposition.ARCHIVE
    }
    
    if disp_choice not in disposition_map:
        print("Invalid disposition choice!")
        return
    
    disposition = disposition_map[disp_choice]
    
    result = control_system.move_paper_to_output(paper_id, disposition)
    
    if result['success']:
        print(f"\n✓ Paper {result['paper_id']} moved to output")
        print(f"  Disposition: {result['disposition']}")
        print(f"  Status: {result['status']}")
        print(f"  Next: {result['next_step']}")
    else:
        print(f"\n✗ Error: {result['error']}")


def view_active_bins(control_system: PaperControlSystem):
    """View all active bins"""
    print("\n--- Active Bins (Unprocessed) ---")
    bins = control_system.get_active_output_bins()
    
    if not bins:
        print("No active bins!")
        return
    
    for bin in bins:
        print(f"\nBin ID: {bin['bin_id']}")
        print(f"  Disposition: {bin['disposition']}")
        print(f"  Paper Count: {bin['paper_count']}/{bin['capacity']}")
        print(f"  Full: {'Yes' if bin['is_full'] else 'No'}")
        print(f"  Created: {bin['created_at']}")


def view_bins_by_disposition(control_system: PaperControlSystem):
    """View bins filtered by disposition"""
    print("\n--- View Bins by Disposition ---")
    print("1. Return Bins")
    print("2. Shred Bins")
    print("3. Archive Bins")
    
    choice = input("Select disposition (1-3): ").strip()
    
    disposition_map = {
        '1': OutputDisposition.RETURN,
        '2': OutputDisposition.SHRED,
        '3': OutputDisposition.ARCHIVE
    }
    
    if choice not in disposition_map:
        print("Invalid choice!")
        return
    
    disposition = disposition_map[choice]
    bins = control_system.get_output_bins_by_disposition(disposition)
    
    if not bins:
        print(f"No bins found for {disposition.value}!")
        return
    
    print(f"\n--- {disposition.value.upper()} Bins ---")
    for bin in bins:
        print(f"\nBin ID: {bin['bin_id']}")
        print(f"  Paper Count: {bin['paper_count']}/{bin['capacity']}")
        print(f"  Full: {'Yes' if bin['is_full'] else 'No'}")
        print(f"  Created: {bin['created_at']}")
        if bin['processed_at']:
            print(f"  Processed: {bin['processed_at']}")


def mark_bin_returned(control_system: PaperControlSystem):
    """Mark a bin as returned"""
    print("\n--- Mark Bin as Returned ---")
    
    # Show return bins
    bins = control_system.get_output_bins_by_disposition(OutputDisposition.RETURN)
    if not bins:
        print("No return bins available!")
        return
    
    print("Available Return Bins:")
    for bin in bins:
        if bin['processed_at'] is None:
            print(f"  {bin['bin_id']} - {bin['paper_count']} papers")
    
    bin_id = input("\nEnter Bin ID to mark as returned: ").strip()
    if not bin_id:
        print("Bin ID required!")
        return
    
    confirm = input(f"Confirm marking {bin_id} as RETURNED? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("Cancelled.")
        return
    
    result = control_system.mark_bin_returned(bin_id)
    
    if result['success']:
        print(f"\n✓ Bin {result['bin_id']} marked as returned")
        print(f"  Papers processed: {result['paper_count']}")
        print(f"  Status: {result['status']}")
    else:
        print(f"\n✗ Error: {result['error']}")


def mark_bin_shredded(control_system: PaperControlSystem):
    """Mark a bin as shredded"""
    print("\n--- Mark Bin as Shredded ---")
    
    # Show shred bins
    bins = control_system.get_output_bins_by_disposition(OutputDisposition.SHRED)
    if not bins:
        print("No shred bins available!")
        return
    
    print("Available Shred Bins:")
    for bin in bins:
        if bin['processed_at'] is None:
            print(f"  {bin['bin_id']} - {bin['paper_count']} papers")
    
    bin_id = input("\nEnter Bin ID to mark as shredded: ").strip()
    if not bin_id:
        print("Bin ID required!")
        return
    
    confirm = input(f"Confirm marking {bin_id} as SHREDDED? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("Cancelled.")
        return
    
    result = control_system.mark_bin_shredded(bin_id)
    
    if result['success']:
        print(f"\n✓ Bin {result['bin_id']} marked as shredded")
        print(f"  Papers processed: {result['paper_count']}")
        print(f"  Status: {result['status']}")
    else:
        print(f"\n✗ Error: {result['error']}")


def view_papers_awaiting_return(control_system: PaperControlSystem):
    """View papers waiting to be returned"""
    print("\n--- Papers Awaiting Return ---")
    papers = control_system.output_rack.get_papers_awaiting_return()
    
    if not papers:
        print("No papers awaiting return!")
        return
    
    print(f"Total: {len(papers)} papers\n")
    for paper in papers:
        print(f"Paper ID: {paper.paper_id}")
        print(f"  Original Box: {paper.box_id}")
        print(f"  Status: {paper.status.value}")
        print(f"  Pages: {paper.pages}")
        print()


def view_papers_awaiting_shredding(control_system: PaperControlSystem):
    """View papers waiting to be shredded"""
    print("\n--- Papers Awaiting Shredding ---")
    papers = control_system.output_rack.get_papers_awaiting_shredding()
    
    if not papers:
        print("No papers awaiting shredding!")
        return
    
    print(f"Total: {len(papers)} papers\n")
    for paper in papers:
        print(f"Paper ID: {paper.paper_id}")
        print(f"  Original Box: {paper.box_id}")
        print(f"  Status: {paper.status.value}")
        print(f"  Pages: {paper.pages}")
        print()


def main():
    """Main CLI loop"""
    print("Initializing Output Rack Control System...")
    control_system = PaperControlSystem()
    
    while True:
        display_menu()
        choice = input("\nSelect option (1-9): ").strip()
        
        if choice == '1':
            view_status(control_system)
        elif choice == '2':
            move_paper_to_output(control_system)
        elif choice == '3':
            view_active_bins(control_system)
        elif choice == '4':
            view_bins_by_disposition(control_system)
        elif choice == '5':
            mark_bin_returned(control_system)
        elif choice == '6':
            mark_bin_shredded(control_system)
        elif choice == '7':
            view_papers_awaiting_return(control_system)
        elif choice == '8':
            view_papers_awaiting_shredding(control_system)
        elif choice == '9':
            print("\nExiting Output Rack System. Goodbye!")
            sys.exit(0)
        else:
            print("\n✗ Invalid option. Please select 1-9.")
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()
