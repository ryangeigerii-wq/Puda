"""
QC Zone CLI Interface
Command-line tool for quality control checks and rescans
"""
import sys
from src.physical.control import PaperControlSystem


def print_header():
    """Print CLI header"""
    print("\n" + "="*60)
    print("  AI PAPER READER - QC ZONE CONTROL")
    print("  Purpose: Visual checks and rescan management")
    print("="*60 + "\n")


def print_menu():
    """Display main menu"""
    print("\nAvailable Commands:")
    print("  1. Move Papers to QC - Transfer from scanning")
    print("  2. View QC Status - Check zone and statistics")
    print("  3. Start QC Check - Begin checking a paper")
    print("  4. Pass QC Check - Mark paper as passed")
    print("  5. Fail QC Check - Mark paper as failed")
    print("  6. Send for Rescan - Send failed paper back to scanning")
    print("  7. View QC Result - Check specific paper result")
    print("  8. View Statistics - QC pass/fail rates")
    print("  9. Back to Main Menu")
    print()


def qc_zone_menu(control: PaperControlSystem):
    """QC zone management interface"""
    print_header()
    
    while True:
        print_menu()
        choice = input("Enter command (1-9): ").strip()
        
        if choice == '1':
            # Move papers to QC
            move_all = input("Move all scanned papers? (y/n): ").strip().lower()
            
            if move_all == 'y':
                result = control.move_papers_to_qc()
            else:
                paper_ids = input("Enter paper IDs (comma-separated): ").strip().split(',')
                paper_ids = [pid.strip() for pid in paper_ids if pid.strip()]
                result = control.move_papers_to_qc(paper_ids)
            
            if result['success']:
                print(f"\n✅ {result['papers_moved']} papers moved to QC zone!")
                print(f"   Next step: {result['next_step']}")
            else:
                print(f"\n❌ Error: {result['error']}")
        
        elif choice == '2':
            # View QC status
            status = control.get_qc_status()
            stats = status['statistics']
            
            print("\n" + "="*60)
            print(f"QC ZONE STATUS - {status['zone_id']}")
            print("="*60)
            print(f"Papers in review: {status['papers_in_review']}")
            print(f"Papers passed: {status['papers_passed']}")
            print(f"Papers failed: {status['papers_failed']}")
            print(f"Papers needing rescan: {status['papers_needing_rescan']}")
            print(f"Total papers: {status['total_papers']}/{status['capacity']}")
            
            print("\n📊 STATISTICS")
            print(f"Total checked: {stats['total_checked']}")
            print(f"Passed: {stats['passed']} ({stats['pass_rate']:.1f}%)")
            print(f"Failed: {stats['failed']}")
            
            if stats['issue_breakdown']:
                print("\nIssue Breakdown:")
                for issue, count in stats['issue_breakdown'].items():
                    print(f"  - {issue}: {count}")
        
        elif choice == '3':
            # Start QC check
            paper_id = input("Enter Paper ID: ").strip()
            checked_by = input("Your name/ID: ").strip()
            
            result = control.start_qc_check(paper_id, checked_by)
            
            if result['success']:
                print(f"\n✅ QC check started for paper {result['paper_id']}")
                print(f"   Checked by: {result['checked_by']}")
                if result.get('scan_file'):
                    print(f"   Scan file: {result['scan_file']}")
            else:
                print(f"\n❌ Error: {result['error']}")
        
        elif choice == '4':
            # Pass QC check
            paper_id = input("Enter Paper ID: ").strip()
            checked_by = input("Your name/ID: ").strip()
            notes = input("Notes (optional): ").strip()
            
            result = control.complete_qc_check(
                paper_id=paper_id,
                checked_by=checked_by,
                passed=True,
                notes=notes
            )
            
            if result['success']:
                print(f"\n✅ Paper {result['paper_id']} PASSED QC!")
                print(f"   Status: {result['status']}")
                print(f"   Next: {result['next_action']}")
            else:
                print(f"\n❌ Error: {result['error']}")
        
        elif choice == '5':
            # Fail QC check
            paper_id = input("Enter Paper ID: ").strip()
            checked_by = input("Your name/ID: ").strip()
            
            print("\nIssue types:")
            print("  1. poor_quality")
            print("  2. missing_pages")
            print("  3. blurry")
            print("  4. misaligned")
            print("  5. incomplete")
            print("  6. other")
            
            issue_input = input("Enter issue numbers (comma-separated): ").strip()
            issue_map = {
                '1': 'poor_quality',
                '2': 'missing_pages',
                '3': 'blurry',
                '4': 'misaligned',
                '5': 'incomplete',
                '6': 'other'
            }
            
            issues = [issue_map.get(i.strip(), 'other') for i in issue_input.split(',')]
            notes = input("Notes: ").strip()
            needs_rescan = input("Needs rescan? (y/n, default=y): ").strip().lower() != 'n'
            
            result = control.complete_qc_check(
                paper_id=paper_id,
                checked_by=checked_by,
                passed=False,
                issues=issues,
                notes=notes,
                needs_rescan=needs_rescan
            )
            
            if result['success']:
                print(f"\n⚠️  Paper {result['paper_id']} FAILED QC")
                print(f"   Status: {result['status']}")
                print(f"   Issues: {', '.join(result['issues'])}")
                print(f"   Next: {result['next_action']}")
            else:
                print(f"\n❌ Error: {result['error']}")
        
        elif choice == '6':
            # Send for rescan
            paper_id = input("Enter Paper ID: ").strip()
            
            result = control.send_for_rescan(paper_id)
            
            if result['success']:
                print(f"\n✅ Paper {result['paper_id']} sent for rescan")
                print(f"   Rescan attempt: #{result['rescan_count']}")
                print(f"   Status: {result['status']}")
                print(f"   Next: {result['next_step']}")
            else:
                print(f"\n❌ Error: {result['error']}")
        
        elif choice == '7':
            # View QC result
            paper_id = input("Enter Paper ID: ").strip()
            result = control.get_qc_result(paper_id)
            
            if result:
                print("\n" + "="*60)
                print(f"QC RESULT - {result['paper_id']}")
                print("="*60)
                print(f"Checked by: {result['checked_by']}")
                print(f"Checked at: {result['checked_at']}")
                print(f"Result: {'✅ PASSED' if result['passed'] else '❌ FAILED'}")
                
                if result['issues']:
                    print(f"Issues: {', '.join(result['issues'])}")
                
                if result['notes']:
                    print(f"Notes: {result['notes']}")
                
                print(f"Needs rescan: {result['needs_rescan']}")
            else:
                print(f"\n❌ No QC result found for paper {paper_id}")
        
        elif choice == '8':
            # View statistics
            status = control.get_qc_status()
            stats = status['statistics']
            
            print("\n" + "="*60)
            print("QC STATISTICS")
            print("="*60)
            print(f"\nTotal papers checked: {stats['total_checked']}")
            print(f"Passed: {stats['passed']} ({stats['pass_rate']:.1f}%)")
            print(f"Failed: {stats['failed']}")
            print(f"Papers needing rescan: {stats['papers_needing_rescan']}")
            
            if stats['issue_breakdown']:
                print("\n📋 Issue Breakdown:")
                sorted_issues = sorted(stats['issue_breakdown'].items(), key=lambda x: x[1], reverse=True)
                for issue, count in sorted_issues:
                    print(f"  {issue:20s}: {count:3d} occurrences")
        
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
        print("3. Scanning Zone")
        print("4. QC Zone")
        print("5. Exit")
        
        choice = input("\nSelect zone (1-5): ").strip()
        
        if choice == '1':
            print("\nIntake zone - use intake_cli.py")
        elif choice == '2':
            print("\nPrep zone - use prep_cli.py")
        elif choice == '3':
            print("\nScanning zone - use scan_cli.py")
        elif choice == '4':
            qc_zone_menu(control)
        elif choice == '5':
            print("\nExiting. Goodbye!\n")
            sys.exit(0)
        else:
            print("\n❌ Invalid choice. Please enter 1-5.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting. Goodbye!\n")
        sys.exit(0)
