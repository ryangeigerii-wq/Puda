"""
Scanning Zone CLI Interface
Command-line tool for managing scanning stations (ADF and workstations)
"""
import sys
from src.physical.control import PaperControlSystem


def print_header():
    """Print CLI header"""
    print("\n" + "="*60)
    print("  AI PAPER READER - SCANNING ZONE CONTROL")
    print("  Purpose: Digitize papers with ADF + Workstation")
    print("="*60 + "\n")


def print_menu():
    """Display main menu"""
    print("\nAvailable Commands:")
    print("  1. Move Papers to Scanning - Transfer from prep zone")
    print("  2. View Scanning Status - Check zone and stations")
    print("  3. View Available Stations - See ready stations")
    print("  4. Start Scan - Begin scanning a paper")
    print("  5. Complete Scan - Finish scanning (success/fail)")
    print("  6. View Station Details - Check specific station")
    print("  7. View Queue - See papers waiting")
    print("  8. Back to Main Menu")
    print()


def scanning_zone_menu(control: PaperControlSystem):
    """Scanning zone management interface"""
    print_header()
    
    while True:
        print_menu()
        choice = input("Enter command (1-8): ").strip()
        
        if choice == '1':
            # Move papers to scanning
            box_id = input("Enter Box ID: ").strip()
            if not box_id:
                print("❌ Box ID cannot be empty")
                continue
            
            result = control.move_papers_to_scanning(box_id)
            if result['success']:
                print(f"\n✅ {result['papers_moved']} papers moved to scanning zone!")
                print(f"   Box ID: {result['box_id']}")
                print(f"   Paper IDs: {', '.join(result['paper_ids'][:5])}")
                if len(result['paper_ids']) > 5:
                    print(f"   ... and {len(result['paper_ids']) - 5} more")
                print(f"   Next step: {result['next_step']}")
            else:
                print(f"\n❌ Error: {result['error']}")
        
        elif choice == '2':
            # View scanning status
            status = control.get_scanning_status()
            print("\n" + "="*60)
            print(f"SCANNING ZONE STATUS - {status['zone_id']}")
            print("="*60)
            print(f"Papers in queue: {status['papers_in_queue']}")
            print(f"Papers scanning now: {status['papers_scanning']}")
            print(f"Papers scanned: {status['papers_scanned']}")
            print(f"Total papers: {status['total_papers']}/{status['capacity']}")
            print(f"\nStations: {status['total_stations']} total, "
                  f"{status['available_stations']} available, "
                  f"{status['busy_stations']} busy")
            print(f"Papers scanned today: {status['papers_scanned_today']}")
            
            if status['stations']:
                print("\nStation Details:")
                for station in status['stations']:
                    status_icon = "🟢" if station['available'] else "🔴"
                    print(f"  {status_icon} {station['id']} ({station['type']}): "
                          f"{station['scanned_today']} scanned today")
        
        elif choice == '3':
            # View available stations
            scanner_type = input("Scanner type (adf/workstation, press Enter for all): ").strip().lower()
            scanner_type = scanner_type if scanner_type in ['adf', 'workstation'] else None
            
            available = control.get_available_stations(scanner_type)
            
            if available:
                print("\n" + "="*60)
                print("AVAILABLE SCANNING STATIONS")
                print("="*60)
                for station in available:
                    print(f"  🟢 {station['station_id']} ({station['scanner_type']})")
                    print(f"     Scanned today: {station['scanned_today']}")
            else:
                print("\n⚠️  No available stations")
        
        elif choice == '4':
            # Start scan
            paper_id = input("Enter Paper ID: ").strip()
            station_id = input("Station ID (press Enter for auto-assign): ").strip()
            station_id = station_id if station_id else None
            
            result = control.start_scan(paper_id, station_id)
            
            if result['success']:
                print(f"\n✅ Scan started for paper {result['paper_id']}!")
                print(f"   Station: {result['station_id']} ({result['scanner_type']})")
                print(f"   Status: {result['status']}")
            else:
                print(f"\n❌ Error: {result['error']}")
        
        elif choice == '5':
            # Complete scan
            paper_id = input("Enter Paper ID: ").strip()
            success_input = input("Success? (y/n, default=y): ").strip().lower()
            success = success_input != 'n'
            
            output_file = None
            if success:
                output_file = input("Output file path (optional): ").strip()
                output_file = output_file if output_file else None
            
            result = control.complete_scan(paper_id, success, output_file)
            
            if result['success']:
                if result['success']:
                    print(f"\n✅ Scan completed for paper {result['paper_id']}!")
                    print(f"   Status: {result['status']}")
                    print(f"   Station: {result['station_id']}")
                    if result.get('output_file'):
                        print(f"   Output: {result['output_file']}")
                else:
                    print(f"\n⚠️  Scan failed for paper {result['paper_id']}")
                    print(f"   Paper returned to queue for retry")
            else:
                print(f"\n❌ Error: {result['error']}")
        
        elif choice == '6':
            # View station details
            station_id = input("Enter Station ID: ").strip()
            status = control.get_station_status(station_id)
            
            if 'error' not in status:
                print("\n" + "="*60)
                print(f"STATION DETAILS - {status['station_id']}")
                print("="*60)
                print(f"Type: {status['scanner_type'].upper()}")
                print(f"Status: {'🟢 Available' if status['is_available'] else '🔴 Busy'}")
                if status['current_paper']:
                    print(f"Current paper: {status['current_paper']}")
                print(f"Papers scanned today: {status['papers_scanned_today']}")
            else:
                print(f"\n❌ Error: {status['error']}")
        
        elif choice == '7':
            # View queue
            status = control.get_scanning_status()
            queued_count = status['papers_in_queue']
            scanning_count = status['papers_scanning']
            
            print("\n" + "="*60)
            print("SCANNING QUEUE")
            print("="*60)
            print(f"Papers in queue: {queued_count}")
            print(f"Papers being scanned: {scanning_count}")
            print(f"Papers completed: {status['papers_scanned']}")
        
        elif choice == '8':
            return
        
        else:
            print("\n❌ Invalid choice. Please enter 1-8.")


def main():
    """Main CLI entry point"""
    control = PaperControlSystem()
    
    while True:
        print("\n" + "="*60)
        print("  AI PAPER READER - PHYSICAL CONTROL SYSTEM")
        print("="*60)
        print("\n1. Intake Zone")
        print("2. Prep Zone")
        print("3. Scanning Zone")
        print("4. Exit")
        
        choice = input("\nSelect zone (1-4): ").strip()
        
        if choice == '1':
            print("\nIntake zone - use intake_cli.py")
        elif choice == '2':
            print("\nPrep zone - use prep_cli.py")
        elif choice == '3':
            scanning_zone_menu(control)
        elif choice == '4':
            print("\nExiting. Goodbye!\n")
            sys.exit(0)
        else:
            print("\n❌ Invalid choice. Please enter 1-4.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting. Goodbye!\n")
        sys.exit(0)
