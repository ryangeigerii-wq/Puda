"""
Test Document Classifier

Tests the classification capability with sample documents.
"""

import sys
from pathlib import Path

# Sample documents for testing
SAMPLE_DOCUMENTS = {
    'invoice': """
        ACME Corporation
        123 Business Way
        New York, NY 10001
        
        INVOICE
        
        Invoice Number: INV-2024-12345
        Invoice Date: January 15, 2024
        Due Date: February 15, 2024
        
        Bill To:
        Tech Solutions Inc.
        456 Tech Drive
        San Francisco, CA 94102
        
        Description                     Quantity    Unit Price    Amount
        ----------------------------------------------------------------
        Consulting Services (Jan 2024)     40 hrs    $150.00    $6,000.00
        Software License - Annual            1       $500.00      $500.00
        Support & Maintenance               12 mo     $50.00      $600.00
        
        Subtotal:                                                $7,100.00
        Tax (8.5%):                                                $603.50
        ----------------------------------------------------------------
        Total Amount Due:                                        $7,703.50
        
        Payment Terms: Net 30
        Bank Details: Account #123-456-789
        Wire Instructions: Contact billing@acme.com
        
        Thank you for your business!
    """,
    
    'receipt': """
        Best Buy Store #1234
        789 Shopping Boulevard
        Los Angeles, CA 90001
        Phone: (555) 123-4567
        
        *** RECEIPT ***
        
        Date: November 10, 2024
        Time: 2:45 PM PST
        Receipt #: 5678-9012-3456
        Cashier: Sarah M.
        Register: 05
        
        Items Purchased:
        ----------------------------------------------------------------
        Laptop Computer - Dell XPS 15           1    $899.99
        Wireless Mouse - Logitech MX Master     1     $79.99
        USB-C Cable - 6ft                       2     $14.99
        Laptop Case - Protective                1     $39.99
        
        Subtotal:                                    $1,049.95
        Tax (8.5%):                                     $89.25
        ----------------------------------------------------------------
        TOTAL:                                       $1,139.20
        
        Payment Method: Visa ending in 1234
        Card Auth: 456789
        
        Items: 5
        Change: $0.00
        
        Thank you for shopping with Best Buy!
        Visit us online at www.bestbuy.com
        
        Return Policy: 30 days with receipt
    """,
    
    'contract': """
        SOFTWARE LICENSE AND SERVICE AGREEMENT
        
        This Software License and Service Agreement (the "Agreement") is
        entered into as of January 1, 2024 (the "Effective Date") by and
        between:
        
        ACME Software Corporation, a Delaware corporation ("Licensor")
        123 Tech Park Drive
        San Jose, CA 95110
        
        AND
        
        XYZ Enterprise Solutions, Inc., a California corporation ("Licensee")
        456 Business Center
        Los Angeles, CA 90012
        
        RECITALS
        
        WHEREAS, Licensor owns certain proprietary software and related
        documentation (collectively, the "Software");
        
        WHEREAS, Licensee desires to license the Software from Licensor
        for internal business purposes;
        
        WHEREAS, Licensor is willing to grant such license subject to the
        terms and conditions set forth herein;
        
        NOW, THEREFORE, in consideration of the mutual covenants and
        agreements contained herein, the parties agree as follows:
        
        1. GRANT OF LICENSE
        
        1.1 License Grant. Subject to the terms and conditions of this
        Agreement, Licensor hereby grants to Licensee a non-exclusive,
        non-transferable, non-sublicensable license to use the Software
        solely for Licensee's internal business purposes.
        
        1.2 Restrictions. Licensee shall not, and shall not permit any
        third party to: (a) copy, modify, or create derivative works of
        the Software; (b) reverse engineer, decompile, or disassemble
        the Software; (c) rent, lease, lend, sell, sublicense, or
        otherwise transfer rights to the Software.
        
        2. TERM AND TERMINATION
        
        2.1 Term. This Agreement shall commence on the Effective Date and
        shall continue for a period of three (3) years unless earlier
        terminated as provided herein (the "Initial Term").
        
        2.2 Termination for Breach. Either party may terminate this
        Agreement upon thirty (30) days' written notice if the other
        party materially breaches any provision of this Agreement.
        
        3. WARRANTIES AND DISCLAIMERS
        
        3.1 Licensor Warranties. Licensor warrants that it has full right,
        power, and authority to enter into this Agreement and grant the
        licenses granted herein.
        
        3.2 DISCLAIMER. EXCEPT AS EXPRESSLY SET FORTH IN THIS AGREEMENT,
        THE SOFTWARE IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND.
        
        4. INDEMNIFICATION
        
        4.1 Licensor Indemnity. Licensor shall indemnify, defend, and
        hold harmless Licensee from and against any claims arising from
        Licensor's breach of its warranties under Section 3.
        
        5. LIMITATION OF LIABILITY
        
        IN NO EVENT SHALL EITHER PARTY'S AGGREGATE LIABILITY EXCEED THE
        AMOUNTS PAID BY LICENSEE IN THE TWELVE (12) MONTHS PRECEDING THE
        CLAIM.
        
        6. GENERAL PROVISIONS
        
        6.1 Governing Law. This Agreement shall be governed by the laws
        of the State of California.
        
        6.2 Entire Agreement. This Agreement constitutes the entire
        agreement between the parties.
        
        IN WITNESS WHEREOF, the parties have executed this Agreement as of
        the date first written above.
        
        LICENSOR:                           LICENSEE:
        ACME Software Corporation           XYZ Enterprise Solutions, Inc.
        
        By: _______________________         By: _______________________
        Name: John Smith                    Name: Jane Doe
        Title: CEO                          Title: CTO
        Date: January 1, 2024               Date: January 1, 2024
    """,
    
    'form': """
        CALIFORNIA DRIVER LICENSE
        
        DL D1234567
        
        Expires: 01/15/2028
        Issued: 01/15/2024
        Class: C
        
        SMITH
        JOHN DAVID
        
        123 MAIN STREET
        LOS ANGELES, CA 90001
        
        DOB: 05/12/1985
        Sex: M
        Height: 5-10
        Weight: 175 LBS
        Eyes: BRN
        Hair: BRN
        
        Restrictions: NONE
        Endorsements: NONE
        
        DD 01234567890123456789012345678901234567
        
        This is an official California Driver License issued by
        the California Department of Motor Vehicles.
        
        For verification, visit: www.dmv.ca.gov
        
        REAL ID COMPLIANT
        
        *** NOT FOR FEDERAL IDENTIFICATION ***
        
        Organ Donor: YES
    """,
    
    'letter': """
        ACME Corporation
        123 Business Way
        New York, NY 10001
        Phone: (555) 123-4567
        
        November 10, 2024
        
        Mr. John Smith
        Tech Solutions Inc.
        456 Tech Drive
        San Francisco, CA 94102
        
        Dear Mr. Smith,
        
        Re: Proposal for Consulting Services
        
        Thank you for your interest in ACME Corporation's consulting
        services. We are pleased to submit this proposal for your review.
        
        ACME Corporation has over 20 years of experience providing
        technology consulting services to Fortune 500 companies. Our
        team of experts specializes in digital transformation, cloud
        migration, and enterprise architecture.
        
        Based on our initial discussions, we propose the following scope
        of work:
        
        1. Assessment Phase (4 weeks)
           - Current state analysis
           - Gap analysis
           - Recommendations report
        
        2. Implementation Phase (12 weeks)
           - Solution design
           - Development and configuration
           - Testing and quality assurance
        
        3. Support Phase (Ongoing)
           - Help desk support
           - Maintenance and updates
           - Training and documentation
        
        We estimate the total project cost at $150,000, broken down into
        monthly installments. Detailed pricing is attached separately.
        
        We would be delighted to discuss this proposal with you at your
        convenience. Please feel free to contact me directly at
        (555) 123-4567 or john.doe@acme.com.
        
        We look forward to the opportunity to work with Tech Solutions Inc.
        
        Sincerely,
        
        
        John Doe
        Vice President, Business Development
        ACME Corporation
        
        Enclosures:
        - Detailed Pricing Sheet
        - Company Brochure
        - References
    """,
    
    'memo': """
        MEMORANDUM
        
        TO:      All Department Heads
        FROM:    Sarah Johnson, Director of Operations
        DATE:    November 10, 2024
        RE:      Updated Remote Work Policy
        
        ================================================================
        
        This memo serves to inform all department heads of the updated
        remote work policy effective December 1, 2024.
        
        BACKGROUND
        
        Following our employee survey and executive review, we have
        decided to implement a hybrid work model that provides greater
        flexibility while maintaining productivity and collaboration.
        
        NEW POLICY HIGHLIGHTS
        
        1. Hybrid Schedule
           - Employees may work remotely up to 3 days per week
           - Core office days: Tuesday and Thursday (all staff required)
           - Flexible remote days: Monday, Wednesday, Friday
        
        2. Remote Work Requirements
           - Maintain regular work hours (9 AM - 5 PM)
           - Remain available via Slack and email
           - Attend all scheduled meetings (virtual or in-person)
           - Complete weekly status reports
        
        3. Equipment and Support
           - Company-provided laptops for all remote workers
           - VPN access for secure connection
           - IT helpdesk available 8 AM - 6 PM
        
        4. Performance Expectations
           - No change to performance standards
           - Regular check-ins with managers
           - Quarterly performance reviews continue
        
        ACTION REQUIRED
        
        Please schedule team meetings to:
        1. Review this policy with your staff
        2. Collect remote work preferences
        3. Submit team schedules to HR by November 20
        4. Address any questions or concerns
        
        QUESTIONS
        
        If you have questions about this policy, please contact:
        - HR Department: hr@company.com
        - IT Support: itsupport@company.com
        - Operations: operations@company.com
        
        Thank you for your cooperation in implementing this new policy.
        
        /s/ Sarah Johnson
        Director of Operations
    """,
    
    'report': """
        QUARTERLY SALES REPORT
        Q3 2024 Performance Analysis
        
        Prepared by: Analytics Department
        Date: October 15, 2024
        Distribution: Executive Team, Sales Leadership
        
        ================================================================
        
        EXECUTIVE SUMMARY
        
        This report presents the Q3 2024 sales performance analysis for
        ACME Corporation. Key findings indicate strong growth in the
        enterprise segment (+35% YoY) and continued challenges in the
        SMB market (-8% YoY).
        
        Overall Q3 revenue reached $12.5M, representing 15% growth
        compared to Q3 2023. However, this falls short of the forecasted
        $13.2M target by 5.3%.
        
        INTRODUCTION
        
        The purpose of this analysis is to:
        1. Evaluate Q3 2024 sales performance against targets
        2. Identify trends and patterns in customer behavior
        3. Assess the effectiveness of current sales strategies
        4. Provide recommendations for Q4 initiatives
        
        METHODOLOGY
        
        Data Sources:
        - CRM system (Salesforce)
        - Financial reporting system
        - Customer surveys (n=500)
        - Sales team interviews (n=25)
        
        Analysis Period: July 1 - September 30, 2024
        
        FINDINGS
        
        1. Revenue Performance
           - Total Revenue: $12,500,000
           - Target: $13,200,000
           - Variance: -5.3%
           
        2. Segment Analysis
           
           Enterprise (>$100K deals):
           - Revenue: $7,500,000 (60% of total)
           - Growth: +35% YoY
           - Win rate: 42%
           - Average deal size: $250,000
           
           Mid-Market ($25K-$100K):
           - Revenue: $3,500,000 (28% of total)
           - Growth: +12% YoY
           - Win rate: 38%
           - Average deal size: $45,000
           
           SMB (<$25K):
           - Revenue: $1,500,000 (12% of total)
           - Growth: -8% YoY
           - Win rate: 28%
           - Average deal size: $12,000
        
        3. Geographic Performance
           - North America: $7,800,000 (62%)
           - Europe: $3,200,000 (26%)
           - Asia-Pacific: $1,500,000 (12%)
        
        4. Product Performance
           - Cloud Platform: $6,250,000 (50%)
           - Professional Services: $3,750,000 (30%)
           - Support Contracts: $2,500,000 (20%)
        
        ANALYSIS
        
        The strong enterprise performance was driven by three factors:
        1. Successful launch of Enterprise Plus tier
        2. Strategic partnerships with systems integrators
        3. Enhanced customer success program
        
        SMB challenges stem from:
        1. Increased competition from low-cost providers
        2. Longer sales cycles (avg 90 days vs 60 days in Q2)
        3. Higher churn rate (15% vs 8% historical average)
        
        RECOMMENDATIONS
        
        1. Double down on enterprise segment
           - Increase enterprise sales team by 20%
           - Develop more enterprise-specific features
           - Create dedicated customer success teams
        
        2. Reevaluate SMB strategy
           - Consider freemium model
           - Implement self-service onboarding
           - Explore channel partnerships
        
        3. Geographic expansion
           - Increase investment in APAC region
           - Hire local sales leadership
           - Develop region-specific go-to-market strategies
        
        CONCLUSION
        
        While Q3 results fell slightly short of targets, the strong
        enterprise performance and continued product innovation position
        ACME Corporation well for Q4 and beyond. Implementation of the
        recommended strategies should help address current challenges
        and accelerate growth.
        
        APPENDICES
        
        Appendix A: Detailed Financial Tables
        Appendix B: Customer Survey Results
        Appendix C: Competitive Analysis
        Appendix D: Sales Team Feedback Summary
        
        ================================================================
        
        For questions regarding this report, contact:
        Analytics Department
        analytics@acme.com
        (555) 123-4567
    """
}


def test_classifier():
    """Test classifier with sample documents."""
    try:
        from src.ml.classifier import DocumentClassifier
        
        print("Document Classifier Test")
        print("=" * 70)
        print()
        
        # Initialize classifier
        print("Initializing classifier...")
        try:
            classifier = DocumentClassifier()
            print("✓ Classifier loaded")
        except Exception as e:
            print(f"✗ Error loading classifier: {e}")
            print("\nNote: This test requires a trained model.")
            print("Train a model first with:")
            print("  python -m src.training.train --data data/train.json --epochs 3 --task classify")
            return
        
        print()
        print("Supported document types:")
        for doc_type in classifier.get_supported_types():
            print(f"  - {doc_type}")
        
        print()
        print("=" * 70)
        print()
        
        # Test each document type
        for doc_type, text in SAMPLE_DOCUMENTS.items():
            print(f"Testing: {doc_type.upper()}")
            print("-" * 70)
            
            try:
                result = classifier.explain_classification(text, top_k=3)
                
                print(f"Prediction: {result['prediction']}")
                print(f"Confidence: {result['confidence']:.4f} ({result['confidence']*100:.2f}%)")
                print(f"Needs Review: {'Yes' if result['needs_review'] else 'No'}")
                
                print("\nTop 3 Predictions:")
                for i, exp in enumerate(result['explanations'], 1):
                    print(f"  {i}. {exp['doc_type']}: {exp['confidence']}")
                    if exp['keywords_found']:
                        keywords = ', '.join(exp['keywords_found'][:3])
                        print(f"     Keywords: {keywords}")
                
                # Check if prediction is correct
                if result['prediction'] == doc_type:
                    print("\n✓ Correct classification!")
                else:
                    print(f"\n✗ Misclassified (expected: {doc_type})")
            
            except Exception as e:
                print(f"✗ Error: {e}")
            
            print()
            print("=" * 70)
            print()
    
    except ImportError as e:
        print(f"Error: {e}")
        print("Classifier module not available")
        sys.exit(1)


def test_batch_classification():
    """Test batch classification."""
    try:
        from src.ml.classifier import DocumentClassifier
        
        print("\nBatch Classification Test")
        print("=" * 70)
        
        classifier = DocumentClassifier()
        
        # Prepare batch
        texts = [text for text in SAMPLE_DOCUMENTS.values()]
        expected_types = list(SAMPLE_DOCUMENTS.keys())
        
        print(f"Classifying {len(texts)} documents in batch...")
        
        results = classifier.classify_batch(texts, batch_size=4)
        
        print("\nResults:")
        print("-" * 70)
        
        correct = 0
        for i, (result, expected) in enumerate(zip(results, expected_types)):
            match = "✓" if result['doc_type'] == expected else "✗"
            print(f"{match} Document {i+1}: {result['doc_type']} "
                  f"(confidence: {result['confidence']:.2%}, "
                  f"expected: {expected})")
            if result['doc_type'] == expected:
                correct += 1
        
        accuracy = correct / len(results) * 100
        print(f"\nAccuracy: {accuracy:.1f}% ({correct}/{len(results)})")
    
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_classifier()
    test_batch_classification()
