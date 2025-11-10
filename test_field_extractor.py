"""
Test Field Extractor

Tests extraction of dates, amounts, and names from sample documents.
"""

import sys
from pathlib import Path

# Sample documents with various field formats
SAMPLE_DOCUMENTS = {
    'invoice': """
        ACME Corporation
        123 Business Way, New York, NY 10001
        Phone: (555) 123-4567
        
        INVOICE
        
        Invoice Number: INV-2024-12345
        Invoice Date: January 15, 2024
        Due Date: 02/15/2024
        
        Bill To:
        John Smith
        Tech Solutions Inc.
        456 Tech Drive
        San Francisco, CA 94102
        
        Attention: Jane Doe, Accounts Payable
        
        Description                          Quantity    Unit Price      Amount
        --------------------------------------------------------------------
        Consulting Services (January 2024)      40 hrs    $150.00      $6,000.00
        Software License - Annual                  1      $500.00        $500.00
        Support & Maintenance (12 months)         12       $50.00        $600.00
        
        Subtotal:                                                       $7,100.00
        Tax (8.5%):                                                       $603.50
        --------------------------------------------------------------------
        Total Amount Due:                                               $7,703.50
        
        Payment Terms: Net 30
        Bank Wire: Account #123-456-789
        
        Authorized by: Sarah Johnson
        Date: 2024-01-15
        
        Contact: billing@acme.com | Phone: +1-555-123-4567
    """,
    
    'receipt': """
        Best Buy Store #1234
        789 Shopping Boulevard
        Los Angeles, CA 90001
        (555) 123-4567
        
        *** SALES RECEIPT ***
        
        Date: November 10, 2024
        Time: 2:45 PM PST
        Receipt #: 5678-9012-3456
        Cashier: Michael Chen
        Register: 05
        
        Customer: Robert Williams
        Rewards Member #: 987654321
        
        Items Purchased:
        --------------------------------------------------------------------
        Dell XPS 15 Laptop                   1        $899.99
        Logitech MX Master Mouse             1         $79.99
        USB-C Cable 6ft                      2         $14.99
        Laptop Protective Case               1         $39.99
        Microsoft Office 365 (1yr)           1         $99.99
        
        Subtotal:                                    $1,149.94
        Tax (8.5%):                                     $97.74
        --------------------------------------------------------------------
        TOTAL:                                       $1,247.68
        
        Payment Method: Visa ending in 1234
        Card Authorization: 456789
        
        Amount Tendered:                             $1,247.68
        Change Due:                                      $0.00
        
        Items: 6
        
        Thank you for shopping with Best Buy!
        Return Policy: 30 days with receipt
        
        Visit us online at www.bestbuy.com
        Rewards Points Earned: 1,248
    """,
    
    'contract': """
        SOFTWARE LICENSE AND MAINTENANCE AGREEMENT
        
        This Software License and Maintenance Agreement (the "Agreement") is
        entered into as of January 1, 2024 (the "Effective Date") by and
        between:
        
        ACME Software Corporation
        ("Licensor")
        123 Tech Park Drive
        San Jose, CA 95110
        Contact: Thomas Anderson, CEO
        
        AND
        
        XYZ Enterprise Solutions, Inc.
        ("Licensee")
        456 Business Center
        Los Angeles, CA 90012
        Contact: Emily Rodriguez, CTO
        
        WHEREAS, Licensor owns proprietary software (the "Software");
        WHEREAS, Licensee desires to license the Software;
        
        NOW, THEREFORE, the parties agree as follows:
        
        1. LICENSE GRANT
        
        1.1 Grant. Subject to the terms herein, Licensor grants Licensee a
        non-exclusive license to use the Software.
        
        1.2 License Fee. Licensee shall pay Licensor a one-time license fee
        of Fifty Thousand Dollars ($50,000.00) due within thirty (30) days
        of the Effective Date.
        
        2. MAINTENANCE AND SUPPORT
        
        2.1 Maintenance Fee. Licensee shall pay an annual maintenance fee of
        Ten Thousand Dollars ($10,000.00) payable on January 1st of each
        year, beginning January 1, 2025.
        
        2.2 Support. Licensor shall provide email and phone support during
        business hours (9:00 AM - 5:00 PM Pacific Time, Monday-Friday).
        
        3. TERM AND TERMINATION
        
        3.1 Initial Term. This Agreement commences on 01/01/2024 and continues
        for three (3) years ending on December 31, 2026.
        
        3.2 Renewal. This Agreement automatically renews for successive one-year
        terms unless either party provides ninety (90) days written notice.
        
        4. PAYMENT TERMS
        
        All payments shall be made to:
        ACME Software Corporation
        Bank: Wells Fargo, Account: 9876543210
        
        Late payments incur interest at 1.5% per month.
        
        5. GENERAL PROVISIONS
        
        5.1 Governing Law. California law governs this Agreement.
        
        5.2 Entire Agreement. This Agreement constitutes the entire agreement
        between the parties and supersedes all prior agreements.
        
        IN WITNESS WHEREOF, the parties have executed this Agreement.
        
        LICENSOR:                               LICENSEE:
        ACME Software Corporation              XYZ Enterprise Solutions, Inc.
        
        By: Thomas Anderson                     By: Emily Rodriguez
        Name: Thomas Anderson                   Name: Emily Rodriguez
        Title: CEO                              Title: CTO
        Date: January 1, 2024                   Date: January 1, 2024
        
        Witness: David Kim                      Witness: Lisa Chen
        Date: 01/01/2024                        Date: 01/01/2024
    """,
    
    'multi_format': """
        QUARTERLY FINANCIAL REPORT
        Q3 2024
        
        Prepared by: Financial Analysis Team
        Report Date: October 15, 2024
        Distribution: Executive Leadership
        
        Contact: Jennifer Martinez, CFO
        Email: j.martinez@company.com
        Phone: (555) 987-6543
        
        KEY DATES:
        - Quarter Start: July 1, 2024
        - Quarter End: September 30, 2024
        - Board Review: 10/22/2024
        - Publication: Oct 31, 2024
        
        REVENUE SUMMARY:
        
        Total Revenue:              $12,500,000.00
        Product Sales:              $8,750,000.00
        Service Revenue:            $3,250,000.00
        Other Income:                 $500,000.00
        
        EXPENSES:
        
        Operating Expenses:         $7,800,000
        Marketing:                  $1,200,000
        R&D:                        $1,800,000.00
        Administrative:               $650,000
        
        Net Income:                 $4,050,000.00
        
        YEAR-OVER-YEAR COMPARISON:
        
        Q3 2023 Revenue: $10,875,000
        Q3 2024 Revenue: $12,500,000
        Growth: +$1,625,000 (+14.9%)
        
        KEY PERSONNEL:
        - CEO: Michael Brown
        - CFO: Jennifer Martinez  
        - COO: David Lee
        - CTO: Sarah Johnson
        
        APPROVAL:
        
        Prepared by: Jennifer Martinez, CFO
        Reviewed by: Michael Brown, CEO
        Approved by: Board of Directors
        Approval Date: October 22, 2024
        
        IMPORTANT DATES AHEAD:
        - Q4 End: 12/31/2024
        - Annual Report Due: January 31, 2025
        - Shareholder Meeting: February 15, 2025
        - Dividend Payment: 03/01/2025
    """
}


def test_field_extractor():
    """Test field extractor with sample documents."""
    try:
        from src.ml.field_extractor import FieldExtractor
        
        print("Field Extractor Test")
        print("=" * 70)
        print()
        
        extractor = FieldExtractor()
        
        for doc_name, text in SAMPLE_DOCUMENTS.items():
            print(f"Testing: {doc_name.upper()}")
            print("-" * 70)
            
            try:
                results = extractor.extract_all(text)
                
                # Dates
                dates = results['dates']
                print(f"\nDates Found: {len(dates)}")
                for i, date in enumerate(dates[:5], 1):
                    print(f"  {i}. {date['text']}", end="")
                    if date.get('normalized'):
                        print(f" → {date['normalized']}", end="")
                    print(f" (confidence: {date['confidence']:.2%})")
                
                # Amounts
                amounts = results['amounts']
                print(f"\nAmounts Found: {len(amounts)}")
                for i, amount in enumerate(amounts[:5], 1):
                    print(f"  {i}. {amount['text']} = {amount['currency']} {amount['value']:,.2f}")
                    print(f"     Type: {amount['type']}, Confidence: {amount['confidence']:.2%}")
                
                # Names
                names = results['names']
                print(f"\nNames Found: {len(names)}")
                for i, name in enumerate(names[:5], 1):
                    print(f"  {i}. {name['text']} ({name['role']})")
                    print(f"     Confidence: {name['confidence']:.2%}")
                
                # Summary stats
                print(f"\nSummary: {len(dates)} dates, {len(amounts)} amounts, {len(names)} names")
                
                if dates and dates[0].get('normalized'):
                    print(f"Primary Date: {dates[0]['text']} ({dates[0]['normalized']})")
                
                if amounts:
                    # Find the highest amount (likely total)
                    max_amount = max(amounts, key=lambda x: x['value'])
                    print(f"Highest Amount: {max_amount['text']} ({max_amount['type']})")
                
                if names:
                    print(f"Primary Contact: {names[0]['text']} ({names[0]['role']})")
                
            except Exception as e:
                print(f"✗ Error: {e}")
            
            print()
            print("=" * 70)
            print()
    
    except ImportError as e:
        print(f"Error: {e}")
        print("Field extractor module not available")
        sys.exit(1)


def test_specific_formats():
    """Test extraction of specific date/amount formats."""
    print("\nSpecific Format Tests")
    print("=" * 70)
    
    from src.ml.field_extractor import FieldExtractor
    extractor = FieldExtractor()
    
    test_cases = [
        ("ISO Date", "Report date: 2024-01-15"),
        ("US Date", "Invoice dated 01/15/2024"),
        ("Written Date", "Effective as of January 15, 2024"),
        ("European Date", "Date: 15.01.2024"),
        ("Dollar Amount", "Total: $1,234.56"),
        ("Euro Amount", "Price: €999.99"),
        ("Plain Amount", "Balance: 1,500.00"),
        ("Multiple Amounts", "Subtotal: $100.00, Tax: $8.50, Total: $108.50"),
        ("Person Name", "Contact: John Smith"),
        ("Name in Context", "Prepared by Sarah Johnson on 2024-01-15"),
    ]
    
    for test_name, text in test_cases:
        print(f"\n{test_name}: '{text}'")
        results = extractor.extract_all(text)
        
        if results['dates']:
            print(f"  ✓ Date: {results['dates'][0]['text']}")
        if results['amounts']:
            print(f"  ✓ Amount: {results['amounts'][0]['text']} = {results['amounts'][0]['value']}")
        if results['names']:
            print(f"  ✓ Name: {results['names'][0]['text']}")


def test_confidence_scoring():
    """Test confidence scoring for different contexts."""
    print("\n\nConfidence Scoring Tests")
    print("=" * 70)
    
    from src.ml.field_extractor import FieldExtractor
    extractor = FieldExtractor()
    
    test_texts = [
        ("High Confidence Date", "Invoice Date: January 15, 2024"),
        ("Low Confidence Date", "Phone: 2024-01-15"),
        ("High Confidence Amount", "Total Amount Due: $1,234.56"),
        ("Low Confidence Amount", "Reference: 1234.56"),
        ("High Confidence Name", "Authorized by: John Smith"),
        ("Low Confidence Name", "John Smith Inc."),
    ]
    
    for test_name, text in test_texts:
        print(f"\n{test_name}: '{text}'")
        results = extractor.extract_all(text)
        
        for field_type in ['dates', 'amounts', 'names']:
            if results[field_type]:
                item = results[field_type][0]
                confidence = item['confidence']
                level = "HIGH" if confidence >= 0.8 else "MEDIUM" if confidence >= 0.6 else "LOW"
                print(f"  {field_type.upper()}: {item['text']} - {confidence:.2%} ({level})")


if __name__ == "__main__":
    test_field_extractor()
    test_specific_formats()
    test_confidence_scoring()
    
    print("\n" + "=" * 70)
    print("All tests complete!")
    print("=" * 70)
