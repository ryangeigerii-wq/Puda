"""
Demo: Warehouse structured data format

Shows the expected structured_data output format from /analyze endpoint.
This demonstrates the CSV/Excel-ready format without requiring the full API.
"""

import json
from datetime import datetime

# Simulated structured data output from /analyze endpoint
# This is the format you'll receive when calling the API


def generate_sample_structured_data():
    """Generate sample structured data as returned by /analyze endpoint."""
    
    # Example 1: Invoice
    invoice_data = {
        "scan_timestamp": datetime.now().isoformat(),
        "document_type": "invoice",
        "classification_confidence": 0.9547,
        
        "text_preview": "ACME Corporation Invoice #INV-2024-12345 Date: 2024-01-15 Amount: $1,984.56",
        "full_text": "ACME Corporation\n123 Business Way\nNew York, NY 10001\n\nINVOICE\n\nInvoice Number: INV-2024-12345\nDate: 2024-01-15\n\nBill To:\nJohn Smith\nTech Solutions Inc.\n456 Tech Drive\nSan Francisco, CA 94102\n\nDescription                     Amount\n------------------------------------\nConsulting Services            $1,234.56\nSoftware License              $500.00\nSupport & Maintenance         $250.00\n                              --------\nTotal Due:                    $1,984.56\n\nPayment Terms: Net 30\nContact: billing@acme.com\nPhone: +1-555-0123",
        "summary": "Invoice from ACME Corporation dated 2024-01-15 for consulting services, software license, and support totaling $1,984.56",
        
        "date": "2024-01-15",
        "date_confidence": 0.9812,
        
        "amount": "$1,984.56",
        "amount_confidence": 0.9534,
        
        "invoice_number": "INV-2024-12345",
        "invoice_confidence": 0.9923,
        
        "organization": "ACME Corporation",
        "organization_confidence": 0.9687,
        
        "contact_name": "John Smith",
        "name_confidence": 0.9234,
        
        "address": "123 Business Way, New York, NY 10001",
        "address_confidence": 0.8876,
        
        "email": "billing@acme.com",
        "phone": "+1-555-0123",
        
        "total_dates": 1,
        "total_amounts": 4,
        "total_organizations": 2,
        "total_entities": 12,
        
        "processing_status": "completed",
        "requires_review": "no",
        
        "ocr_confidence": "",
        "ocr_language": "",
        "ocr_word_count": "",
    }
    
    # Example 2: Receipt
    receipt_data = {
        "scan_timestamp": datetime.now().isoformat(),
        "document_type": "receipt",
        "classification_confidence": 0.9823,
        
        "text_preview": "Best Buy Store #1234 Receipt Date: 11/10/2024 Total: $1,023.12",
        "full_text": "Best Buy Store #1234\n789 Shopping Blvd\nLos Angeles, CA 90001\nTel: (555) 123-4567\n\nRECEIPT\n\nDate: 11/10/2024 2:45 PM\nReceipt #: 5678-9012-3456\n\nItems:\nLaptop Computer          $899.99\nWireless Mouse           $29.99\nUSB Cable                $12.99\n                        -------\nSubtotal:                $942.97\nTax (8.5%):              $80.15\n                        -------\nTOTAL:                   $1,023.12\n\nPayment: Visa ****1234\nThank you for shopping!",
        "summary": "Best Buy receipt for laptop computer, wireless mouse, and USB cable totaling $1,023.12",
        
        "date": "11/10/2024",
        "date_confidence": 0.9956,
        
        "amount": "$1,023.12",
        "amount_confidence": 0.9789,
        
        "invoice_number": "5678-9012-3456",
        "invoice_confidence": 0.9654,
        
        "organization": "Best Buy",
        "organization_confidence": 0.9912,
        
        "contact_name": "",
        "name_confidence": "",
        
        "address": "789 Shopping Blvd, Los Angeles, CA 90001",
        "address_confidence": 0.9123,
        
        "email": "",
        "phone": "(555) 123-4567",
        
        "total_dates": 1,
        "total_amounts": 5,
        "total_organizations": 1,
        "total_entities": 8,
        
        "processing_status": "completed",
        "requires_review": "no",
        
        "ocr_confidence": "",
        "ocr_language": "",
        "ocr_word_count": "",
    }
    
    return [invoice_data, receipt_data]


def export_to_csv_demo():
    """Demonstrate CSV export."""
    import csv
    
    data = generate_sample_structured_data()
    
    # Write to CSV
    output_file = "warehouse_demo.csv"
    
    if data:
        fieldnames = list(data[0].keys())
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        print(f"✓ Exported {len(data)} records to {output_file}")
        print(f"✓ Fields: {len(fieldnames)}")
        print(f"\nFirst 10 fields:")
        for field in fieldnames[:10]:
            print(f"  - {field}")


def export_to_excel_demo():
    """Demonstrate Excel export."""
    try:
        import pandas as pd
        
        data = generate_sample_structured_data()
        
        df = pd.DataFrame(data)
        output_file = "warehouse_demo.xlsx"
        df.to_excel(output_file, index=False, engine='openpyxl')
        
        print(f"\n✓ Exported {len(data)} records to {output_file}")
        print(f"✓ Columns: {len(df.columns)}")
        print(f"\nDataFrame shape: {df.shape}")
        print(f"\nSample data:")
        print(df[['document_type', 'invoice_number', 'date', 'amount', 'organization']].to_string())
        
    except ImportError:
        print("\n✗ pandas/openpyxl not installed")
        print("Install with: pip install pandas openpyxl")


def show_json_structure():
    """Display JSON structure."""
    data = generate_sample_structured_data()
    
    print("\n" + "=" * 80)
    print("WAREHOUSE STRUCTURED DATA FORMAT")
    print("=" * 80)
    
    print("\nExample 1: Invoice Document")
    print("-" * 80)
    print(json.dumps(data[0], indent=2))
    
    print("\n\nExample 2: Receipt Document")
    print("-" * 80)
    print(json.dumps(data[1], indent=2))
    
    print("\n" + "=" * 80)
    print("KEY FEATURES")
    print("=" * 80)
    print("✓ Single-level dictionary (no nesting)")
    print("✓ All values are primitive types (str, float, int)")
    print("✓ Empty fields are empty strings (not null)")
    print("✓ Ready for CSV/Excel export")
    print("✓ Confidence scores for ML predictions")
    print("✓ Review flags for quality control")
    print("=" * 80)


if __name__ == "__main__":
    print("Puda AI - Warehouse Data Export Demo")
    print("=" * 80)
    
    # Show JSON structure
    show_json_structure()
    
    # Export demos
    print("\n\nExporting to CSV...")
    print("-" * 80)
    export_to_csv_demo()
    
    print("\n\nExporting to Excel...")
    print("-" * 80)
    export_to_excel_demo()
    
    print("\n\n" + "=" * 80)
    print("Demo complete! Check the generated files:")
    print("  - warehouse_demo.csv")
    print("  - warehouse_demo.xlsx")
    print("=" * 80)
