"""
Test suite for document summarizer.

Tests extractive, abstractive, and hybrid summarization on various document types.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.ml.summarizer import DocumentSummarizer


# Sample documents for testing
SAMPLE_INVOICE = """
INVOICE #INV-2024-001

Date: January 15, 2024
Due Date: February 15, 2024

Bill To:
Acme Corporation
123 Business Street
New York, NY 10001

From:
Tech Solutions Inc.
456 Service Avenue
San Francisco, CA 94102

DESCRIPTION                          QTY    UNIT PRICE    AMOUNT
Software Development Services         160    $125.00       $20,000.00
Technical Consulting                  40     $150.00       $6,000.00
System Integration                    80     $135.00       $10,800.00

                                      SUBTOTAL:           $36,800.00
                                      TAX (8.5%):         $3,128.00
                                      TOTAL DUE:          $39,928.00

Payment Terms: Net 30 days. Late payments subject to 1.5% monthly interest.
Please make checks payable to Tech Solutions Inc.

Thank you for your business!
"""

SAMPLE_CONTRACT = """
CONSULTING SERVICES AGREEMENT

This Agreement is entered into as of January 1, 2024 (the "Effective Date") 
between Acme Corporation, a Delaware corporation ("Client"), and Tech Solutions Inc., 
a California corporation ("Consultant").

WHEREAS, Client desires to retain Consultant to provide certain consulting services; 
and WHEREAS, Consultant is willing to provide such services on the terms and conditions 
set forth herein.

NOW, THEREFORE, in consideration of the mutual covenants and agreements contained herein, 
the parties agree as follows:

1. SERVICES. Consultant shall provide software development and technical consulting 
services as detailed in Exhibit A ("Services"). The Services shall be performed in 
accordance with industry best practices and Client's reasonable specifications.

2. TERM. This Agreement shall commence on the Effective Date and continue until 
December 31, 2024, unless earlier terminated in accordance with Section 7 ("Term").

3. COMPENSATION. Client shall pay Consultant a total fee of $50,000.00 for the Services, 
payable in monthly installments of $4,166.67 on the first day of each month during 
the Term.

4. CONFIDENTIALITY. Each party agrees to maintain in confidence all Confidential 
Information of the other party and to use such information only for purposes of 
this Agreement.

5. INTELLECTUAL PROPERTY. All work product created by Consultant in connection with 
the Services shall be owned by Client as works made for hire.

6. WARRANTIES. Consultant warrants that the Services will be performed in a 
professional and workmanlike manner.

7. TERMINATION. Either party may terminate this Agreement upon thirty (30) days 
written notice to the other party.

8. GOVERNING LAW. This Agreement shall be governed by the laws of the State of California.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the Effective Date.

ACME CORPORATION                      TECH SOLUTIONS INC.

By: John Smith                        By: Sarah Johnson
Title: CEO                            Title: President
Date: January 1, 2024                 Date: January 1, 2024
"""

SAMPLE_REPORT = """
QUARTERLY SALES REPORT - Q1 2024

Executive Summary:
This report analyzes sales performance for the first quarter of 2024. Overall revenue 
increased by 23% compared to Q1 2023, driven by strong performance in the enterprise 
segment and successful product launches. However, the SMB segment showed slower growth 
due to increased market competition.

Key Findings:

1. Revenue Growth: Total revenue reached $12.5M, exceeding our target of $11M by 14%. 
This represents a year-over-year growth of 23% from Q1 2023's $10.2M.

2. Enterprise Segment: Enterprise sales grew 35% to $8M, accounting for 64% of total 
revenue. The average deal size increased from $125K to $160K, indicating stronger 
value proposition and improved sales efficiency.

3. SMB Segment: SMB revenue grew only 8% to $4.5M. Customer acquisition cost increased 
by 15% while average revenue per customer remained flat, suggesting pricing pressure 
and increased competition in this segment.

4. Product Performance: Our flagship product contributed $9M (72% of revenue), while 
new product releases generated $3.5M. The new products exceeded expectations, reaching 
breakeven two months ahead of schedule.

5. Geographic Distribution: North America accounted for 60% of revenue ($7.5M), 
Europe 30% ($3.75M), and Asia-Pacific 10% ($1.25M). The APAC region showed the 
highest growth rate at 45% year-over-year.

Recommendations:

1. Increase investment in enterprise sales team to capitalize on strong momentum 
and large deal pipeline.

2. Revise SMB pricing strategy to remain competitive while maintaining margin targets.

3. Accelerate product development roadmap based on strong reception of new releases.

4. Expand APAC presence through strategic partnerships and local hiring.

Conclusion:
Q1 2024 demonstrated strong overall performance with notable success in enterprise 
segment. While SMB segment growth was below expectations, the company is well-positioned 
to meet full-year revenue targets of $52M. Focus areas for Q2 include enterprise 
expansion, SMB strategy refinement, and continued product innovation.
"""

SAMPLE_LETTER = """
Dear Mr. Anderson,

I am writing to follow up on our conversation last week regarding the proposed 
partnership between Acme Corporation and Tech Solutions Inc. After careful 
consideration and internal discussions with our executive team, I am pleased 
to inform you that we would like to move forward with the partnership.

We believe that combining Acme's market presence with Tech Solutions' technical 
expertise will create significant value for both organizations. The synergies 
identified during our due diligence process are compelling, particularly in 
the areas of product development, customer service, and market expansion.

Our legal team has begun reviewing the draft partnership agreement you provided. 
We anticipate having our comments and proposed revisions to you by the end of 
next week. In the meantime, I propose that we schedule a meeting for February 1st 
to discuss the operational integration plan and timeline.

Please confirm your availability for the meeting and let me know if you need 
any additional information from our side. I look forward to building a successful 
partnership together.

Best regards,

John Smith
Chief Executive Officer
Acme Corporation
"""

SAMPLE_RECEIPT = """
RECEIPT

Store: TechMart Electronics
Location: 789 Market Street, San Francisco, CA
Store #: 0542
Transaction Date: November 10, 2024
Time: 14:35:22
Cashier: Emma Wilson

ITEMS PURCHASED:
--------------------------------------------------------------
1. Wireless Mouse (Logitech MX Master 3)
   SKU: LG-MX3-BLK
   Price: $99.99 x 1                                    $99.99

2. USB-C Cable (6ft, Anker)
   SKU: ANK-USBC-6FT
   Price: $12.99 x 2                                    $25.98

3. Laptop Stand (Aluminum)
   SKU: LS-ALU-001
   Price: $49.99 x 1                                    $49.99

4. Keyboard Wrist Rest
   SKU: KWR-MEM-BLK
   Price: $19.99 x 1                                    $19.99

--------------------------------------------------------------
SUBTOTAL:                                              $195.95
SALES TAX (9.5%):                                       $18.62
--------------------------------------------------------------
TOTAL:                                                 $214.57

PAYMENT METHOD: Visa ****1234
AUTHORIZATION: 789456
APPROVED

Customer Rewards #: 1234567890
Points Earned: 215
Total Points Balance: 3,847

RETURN POLICY: Returns accepted within 30 days with receipt.
Electronics must be in original packaging with all accessories.

Thank you for shopping at TechMart Electronics!
Visit us online at www.techmart.com
"""

SAMPLE_MEMO = """
MEMORANDUM

TO:       All Department Heads
FROM:     Sarah Johnson, Chief Operating Officer
DATE:     January 15, 2024
SUBJECT:  New Remote Work Policy - Effective February 1, 2024

This memo outlines the updated remote work policy that will take effect on 
February 1, 2024. After careful consideration of employee feedback and 
operational requirements, we are implementing a hybrid work model that 
balances flexibility with collaboration needs.

Key Policy Points:

1. Hybrid Schedule: All employees may work remotely up to 3 days per week. 
Core in-office days are Tuesday and Thursday for department meetings and 
collaborative work.

2. Equipment: The company will provide necessary equipment including laptop, 
monitor, and ergonomic accessories for home offices. Submit equipment requests 
through the IT portal by January 22nd.

3. Communication: Remote workers must be available during core business hours 
(9 AM - 5 PM) and responsive on company communication channels. Video must be 
enabled for all team meetings.

4. Performance: Work quality and deliverables remain the primary evaluation 
criteria. Managers will conduct monthly check-ins to ensure remote arrangements 
are effective.

5. Approval Process: Remote work schedules must be coordinated with direct 
managers to ensure adequate in-office coverage. Submit preferences through 
the HR portal.

Implementation Timeline:
- January 22: Equipment request deadline
- January 25: Manager approval deadline
- January 29-31: Equipment distribution
- February 1: Policy effective date

Please review the complete policy document on the company intranet and 
direct any questions to the HR department. Department heads should schedule 
team meetings this week to discuss implementation details.

Thank you for your cooperation as we implement this new policy designed to 
support both individual flexibility and organizational effectiveness.
"""


def test_summarizer():
    """Test summarizer on various document types."""
    summarizer = DocumentSummarizer()
    
    documents = [
        ("INVOICE", SAMPLE_INVOICE),
        ("CONTRACT", SAMPLE_CONTRACT),
        ("REPORT", SAMPLE_REPORT),
        ("LETTER", SAMPLE_LETTER),
        ("RECEIPT", SAMPLE_RECEIPT),
        ("MEMO", SAMPLE_MEMO)
    ]
    
    print("=" * 80)
    print("DOCUMENT SUMMARIZER TEST SUITE")
    print("=" * 80)
    print()
    
    for doc_type, doc_text in documents:
        print(f"\n{'='*80}")
        print(f"TESTING: {doc_type}")
        print(f"{'='*80}")
        print(f"Original length: {len(doc_text)} chars, {len(doc_text.split())} words")
        print()
        
        # Test all three methods
        methods = ['extractive', 'abstractive', 'hybrid']
        
        for method in methods:
            print(f"\n--- {method.upper()} METHOD ---")
            result = summarizer.summarize(doc_text, method=method, length='medium')
            
            print(f"Summary ({result.statistics['summary_words']} words):")
            print(result.summary)
            print()
            print(f"Confidence: {result.confidence:.1%}")
            print(f"Reduction: {result.reduction_ratio:.1f}%")
            print(f"Doc Type: {result.statistics['document_type']}")
            
            if result.bullet_points:
                print(f"Bullet Points: {len(result.bullet_points)} found")
            
            print()


def test_summary_lengths():
    """Test different summary lengths."""
    summarizer = DocumentSummarizer()
    
    print("\n" + "="*80)
    print("TESTING SUMMARY LENGTHS")
    print("="*80)
    print()
    
    test_text = SAMPLE_REPORT
    lengths = ['short', 'medium', 'long']
    
    for length in lengths:
        result = summarizer.summarize(test_text, method='extractive', length=length)
        
        print(f"\n{length.upper()} Summary:")
        print(f"Words: {result.statistics['summary_words']}")
        print(f"Sentences: {result.statistics['summary_sentences']}")
        print(result.summary[:200] + "..." if len(result.summary) > 200 else result.summary)
        print()


def test_batch_processing():
    """Test batch summarization."""
    summarizer = DocumentSummarizer()
    
    print("\n" + "="*80)
    print("TESTING BATCH PROCESSING")
    print("="*80)
    print()
    
    documents = [SAMPLE_INVOICE, SAMPLE_CONTRACT, SAMPLE_REPORT]
    
    results = summarizer.summarize_batch(documents, method='hybrid', length='short')
    
    print(f"Processed {len(results)} documents")
    print()
    
    for i, result in enumerate(results, 1):
        print(f"\nDocument {i}:")
        print(f"  Type: {result.statistics['document_type']}")
        print(f"  Summary: {result.summary[:100]}...")
        print(f"  Confidence: {result.confidence:.1%}")
        print(f"  Reduction: {result.reduction_ratio:.1f}%")


def test_edge_cases():
    """Test edge cases and error handling."""
    summarizer = DocumentSummarizer()
    
    print("\n" + "="*80)
    print("TESTING EDGE CASES")
    print("="*80)
    print()
    
    # Test empty text
    print("Test: Empty text")
    result = summarizer.summarize("")
    print(f"  Summary: '{result.summary}'")
    print(f"  Confidence: {result.confidence}")
    print()
    
    # Test very short text
    print("Test: Very short text (1 sentence)")
    short_text = "This is a single sentence."
    result = summarizer.summarize(short_text)
    print(f"  Summary: '{result.summary}'")
    print(f"  Confidence: {result.confidence:.1%}")
    print()
    
    # Test text with no sentences
    print("Test: Text with no proper sentences")
    no_sentences = "word1 word2 word3 word4 word5"
    result = summarizer.summarize(no_sentences)
    print(f"  Summary: '{result.summary}'")
    print(f"  Confidence: {result.confidence:.1%}")
    print()
    
    # Test very long text
    print("Test: Very long text")
    long_text = (SAMPLE_REPORT + " " + SAMPLE_CONTRACT) * 3
    result = summarizer.summarize(long_text, length='short')
    print(f"  Original: {len(long_text)} chars, {len(long_text.split())} words")
    print(f"  Summary: {result.statistics['summary_words']} words")
    print(f"  Reduction: {result.reduction_ratio:.1f}%")
    print(f"  Confidence: {result.confidence:.1%}")
    print()


def test_quality_metrics():
    """Test summary quality and consistency."""
    summarizer = DocumentSummarizer()
    
    print("\n" + "="*80)
    print("TESTING QUALITY METRICS")
    print("="*80)
    print()
    
    # Test on report
    result = summarizer.summarize(SAMPLE_REPORT, method='extractive', length='medium')
    
    print("Quality Assessment:")
    print(f"  Confidence: {result.confidence:.1%}")
    print(f"  Reduction Ratio: {result.reduction_ratio:.1f}%")
    print(f"  Sentences Selected: {result.statistics['summary_sentences']}/{result.statistics['original_sentences']}")
    print(f"  Words: {result.statistics['summary_words']}/{result.statistics['original_words']}")
    print()
    
    # Check if key information is preserved
    key_terms = ['revenue', 'enterprise', 'growth', 'Q1', '2024']
    preserved = sum(1 for term in key_terms if term.lower() in result.summary.lower())
    
    print(f"Key Terms Preserved: {preserved}/{len(key_terms)}")
    print(f"Terms: {', '.join(key_terms)}")
    print()
    
    # Test consistency (multiple runs should be deterministic)
    print("Testing consistency (3 runs):")
    summaries = [
        summarizer.summarize(SAMPLE_REPORT, method='extractive', length='medium').summary
        for _ in range(3)
    ]
    
    if all(s == summaries[0] for s in summaries):
        print("  ✓ Consistent results across runs")
    else:
        print("  ✗ Inconsistent results")
    print()


if __name__ == '__main__':
    print("Starting Document Summarizer Test Suite...")
    print()
    
    try:
        test_summarizer()
        test_summary_lengths()
        test_batch_processing()
        test_edge_cases()
        test_quality_metrics()
        
        print("\n" + "="*80)
        print("ALL TESTS COMPLETE!")
        print("="*80)
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
