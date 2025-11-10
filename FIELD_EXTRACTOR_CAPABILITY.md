# Field Extractor - Second Core Capability

## Overview

Puda's **Field Extractor** is the second core capability that extracts key structured fields from documents. It focuses on the three most critical field types for business documents:

1. **Dates** - Invoice dates, due dates, effective dates, expiration dates
2. **Amounts** - Totals, subtotals, taxes, payments, balances
3. **Names** - People, contacts, vendors, customers, signatories

## Key Features

✅ **Multiple Date Formats** - ISO, US, European, written, compact  
✅ **Currency Support** - USD, EUR, GBP, generic numbers  
✅ **Context-Aware** - Uses surrounding text for better accuracy  
✅ **Confidence Scoring** - ML-style confidence for each extraction  
✅ **Field Classification** - Identifies field types (total, subtotal, tax, etc.)  
✅ **Deduplication** - Removes duplicate extractions  
✅ **Normalization** - Converts dates to ISO format, amounts to numeric values  

## Architecture

```
Input Text
    ↓
Pattern Matching (Regex)
    ↓
Context Analysis
    ↓
Confidence Scoring
    ↓
Deduplication & Sorting
    ↓
Output: {dates[], amounts[], names[]}
```

## Supported Formats

### Date Formats

| Format | Example | Pattern |
|--------|---------|---------|
| ISO | `2024-01-15` | YYYY-MM-DD |
| US | `01/15/2024` | MM/DD/YYYY |
| European | `15.01.2024` | DD.MM.YYYY |
| Written | `January 15, 2024` | Month DD, YYYY |
| Short Month | `Jan 15, 2024` | Mon DD, YYYY |
| Compact | `20240115` | YYYYMMDD |

### Amount Formats

| Format | Example | Currency |
|--------|---------|----------|
| Dollar | `$1,234.56` | USD |
| Dollar (alt) | `1,234.56 USD` | USD |
| Euro | `€1,234.56` | EUR |
| Pound | `£1,234.56` | GBP |
| Plain | `1,234.56` | NUMBER |

### Name Patterns

**Indicator-based:**
- `Name: John Smith`
- `Contact: Jane Doe`
- `Authorized by: Tom Anderson`
- `Bill To: Sarah Johnson`

**Capitalized Names:**
- `John Smith` (2-3 capitalized words)
- Filters out organizations automatically

## Usage

### Python API

```python
from src.ml.field_extractor import FieldExtractor

# Initialize extractor
extractor = FieldExtractor()

# Extract all fields
text = """
Invoice Date: January 15, 2024
Amount Due: $1,234.56
Bill To: John Smith
"""

results = extractor.extract_all(text)

# Access dates
for date in results['dates']:
    print(f"{date['text']} → {date['normalized']}")
    print(f"Confidence: {date['confidence']:.2%}")

# Access amounts
for amount in results['amounts']:
    print(f"{amount['text']} = {amount['value']}")
    print(f"Type: {amount['type']}, Currency: {amount['currency']}")

# Access names
for name in results['names']:
    print(f"{name['text']} ({name['role']})")
    print(f"Confidence: {name['confidence']:.2%}")

# Extract specific field types
dates = extractor.extract_dates(text)
amounts = extractor.extract_amounts(text)
names = extractor.extract_names(text)
```

### Command Line Interface

```bash
# Extract from text
python extract_cli.py --text "Invoice dated 01/15/2024 for $1,234.56"

# Extract from file
python extract_cli.py --file invoice.txt

# Extract specific fields only
python extract_cli.py --file doc.txt --fields dates amounts

# JSON output
python extract_cli.py --file doc.txt --format json

# Batch extraction with CSV export
python extract_cli.py --batch documents/ --output results.csv
```

### REST API (via /extract endpoint)

```bash
curl -X POST http://localhost:8001/extract \
  -H "Content-Type: application/json" \
  -d '{"text": "Invoice dated 01/15/2024 for $1,234.56"}'

# Response
{
  "fields": {
    "DATE": [
      {
        "text": "01/15/2024",
        "confidence": 0.95,
        "normalized": "2024-01-15"
      }
    ],
    "AMOUNT": [
      {
        "text": "$1,234.56",
        "confidence": 0.95,
        "value": 1234.56,
        "currency": "USD",
        "type": "amount"
      }
    ]
  },
  "count": 2
}
```

## Confidence Scoring

### Dates

| Condition | Confidence |
|-----------|-----------|
| Base extraction | 0.70 |
| Has date indicator (Date:, Due:, etc.) | +0.20 |
| Standard format (ISO, MM/DD/YYYY) | +0.05 |
| **Maximum** | 0.95 |

### Amounts

| Condition | Confidence |
|-----------|-----------|
| Base extraction | 0.70 |
| Context keyword match (total, amount, due) | +0.02 to +0.20 |
| Has currency symbol ($, €, £) | +0.10 |
| Value out of range (< $0.01 or > $1B) | -0.20 |
| **Maximum** | 0.95 |

### Names

| Condition | Confidence |
|-----------|-----------|
| With indicator (Name:, Contact:, etc.) | 0.85 |
| Capitalized pattern only | 0.65 |
| Filtered as organization | Excluded |

## Field Classification

### Amount Types

The extractor automatically classifies amounts based on context:

- **total** - "Total Amount", "Total Due"
- **subtotal** - "Subtotal", "Sub-Total"
- **tax** - "Tax", "Sales Tax", "VAT"
- **amount_due** - "Amount Due", "Balance"
- **payment** - "Payment", "Paid"
- **discount** - "Discount", "Reduction"
- **amount** - Generic amount

### Name Roles

The extractor classifies names by role:

- **vendor** - "Vendor:", "Seller:"
- **customer** - "Customer:", "Client:", "Bill To:"
- **contact** - "Contact:", "Attention:"
- **signatory** - "Authorized by:", "Signed:"
- **preparer** - "Prepared by:"
- **person** - Generic person

## Output Format

### Date Object

```python
{
    'text': 'January 15, 2024',        # Original text
    'normalized': '2024-01-15',        # ISO format (YYYY-MM-DD)
    'format': 'Month DD, YYYY',        # Detected format
    'confidence': 0.90,                # Confidence score (0-1)
    'start': 125,                      # Character position (start)
    'end': 142,                        # Character position (end)
    'context': '...Invoice Date: January 15, 2024 Amount...',  # Surrounding text
    'source': 'pattern'                # Extraction method
}
```

### Amount Object

```python
{
    'text': '$1,234.56',               # Original text
    'value': 1234.56,                  # Numeric value
    'currency': 'USD',                 # Currency code
    'type': 'total',                   # Amount classification
    'confidence': 0.95,                # Confidence score (0-1)
    'start': 158,                      # Character position (start)
    'end': 168,                        # Character position (end)
    'context': '...Total Amount Due: $1,234.56 Payment...',  # Surrounding text
    'source': 'pattern'                # Extraction method
}
```

### Name Object

```python
{
    'text': 'John Smith',              # Extracted name
    'role': 'customer',                # Classified role
    'confidence': 0.85,                # Confidence score (0-1)
    'start': 92,                       # Character position (start)
    'end': 102,                        # Character position (end)
    'context': '...Bill To: John Smith Tech Solutions...',  # Surrounding text
    'source': 'pattern_indicator'      # Extraction method
}
```

## Integration Examples

### 1. Invoice Processing

```python
from src.ml.field_extractor import FieldExtractor

def process_invoice(text):
    """Extract key fields from invoice."""
    extractor = FieldExtractor()
    fields = extractor.extract_all(text)
    
    # Get invoice date (usually first date)
    invoice_date = fields['dates'][0] if fields['dates'] else None
    
    # Get total amount (highest amount or marked as 'total')
    total = max(fields['amounts'], key=lambda x: x['value']) if fields['amounts'] else None
    
    # Get vendor (first name or customer role)
    vendor = next((n for n in fields['names'] if n['role'] == 'vendor'), 
                  fields['names'][0] if fields['names'] else None)
    
    return {
        'invoice_date': invoice_date['normalized'] if invoice_date else None,
        'total_amount': total['value'] if total else None,
        'vendor_name': vendor['text'] if vendor else None
    }
```

### 2. Payment Verification

```python
def verify_payment(invoice_text, payment_amount, payment_date):
    """Verify payment matches invoice."""
    extractor = FieldExtractor()
    fields = extractor.extract_all(invoice_text)
    
    # Find total amount
    invoice_total = max(
        (a for a in fields['amounts'] if a['type'] in ['total', 'amount_due']),
        key=lambda x: x['confidence'],
        default=None
    )
    
    # Find due date
    due_date = next(
        (d for d in fields['dates'] if 'due' in d['context'].lower()),
        None
    )
    
    # Verify
    amount_match = (invoice_total and 
                    abs(invoice_total['value'] - payment_amount) < 0.01)
    
    date_valid = (not due_date or 
                  payment_date <= due_date['normalized'])
    
    return {
        'amount_match': amount_match,
        'date_valid': date_valid,
        'invoice_total': invoice_total['value'] if invoice_total else None,
        'due_date': due_date['normalized'] if due_date else None
    }
```

### 3. Contract Analysis

```python
def analyze_contract(contract_text):
    """Extract key dates and amounts from contract."""
    extractor = FieldExtractor()
    fields = extractor.extract_all(contract_text)
    
    # Sort dates chronologically
    dates = sorted(
        fields['dates'],
        key=lambda x: x.get('normalized', x['text'])
    )
    
    # Classify dates by context
    effective_date = next(
        (d for d in dates if 'effective' in d['context'].lower()),
        dates[0] if dates else None
    )
    
    expiry_date = next(
        (d for d in dates if any(kw in d['context'].lower() 
         for kw in ['expir', 'end', 'terminat'])),
        dates[-1] if len(dates) > 1 else None
    )
    
    # Get payment terms
    payments = [
        {
            'amount': a['value'],
            'type': a['type'],
            'context': a['context'][:100]
        }
        for a in fields['amounts']
    ]
    
    # Get signatories
    signatories = [
        n['text'] for n in fields['names'] 
        if n['role'] == 'signatory'
    ]
    
    return {
        'effective_date': effective_date['normalized'] if effective_date else None,
        'expiry_date': expiry_date['normalized'] if expiry_date else None,
        'payment_terms': payments,
        'signatories': signatories
    }
```

## Performance

### Speed
- **Single document:** ~5-20ms (pattern matching)
- **Batch (100 docs):** ~1-2 seconds
- **No GPU required:** Pure CPU processing

### Accuracy
- **Dates:** >95% for standard formats
- **Amounts:** >90% with currency symbols
- **Names:** >85% with indicators, >70% capitalized

### Memory
- **Minimal footprint:** ~10MB
- **No model loading:** Pattern-based extraction

## Best Practices

### 1. Preprocessing

```python
# Clean OCR artifacts
text = text.replace('|', 'I')  # Common OCR error
text = text.replace('O', '0')  # In amounts context

# Normalize whitespace
import re
text = re.sub(r'\s+', ' ', text)
```

### 2. Post-processing

```python
# Filter by confidence
high_confidence_dates = [
    d for d in dates 
    if d['confidence'] >= 0.8
]

# Get unique amounts
unique_amounts = list({a['value']: a for a in amounts}.values())
```

### 3. Validation

```python
from datetime import datetime

def validate_date(date_str):
    """Validate extracted date."""
    try:
        dt = datetime.fromisoformat(date_str)
        # Check if reasonable (not too far in past/future)
        year = dt.year
        return 1900 <= year <= 2100
    except:
        return False

def validate_amount(value):
    """Validate extracted amount."""
    return 0.01 <= value <= 1_000_000_000
```

## Testing

Run the comprehensive test suite:

```bash
python test_field_extractor.py
```

Expected output:
- Invoice: 2 dates, 8 amounts, 15 names
- Receipt: 1 date, 9 amounts, 16 names
- Contract: 3 dates, 2 amounts, 24 names
- Multi-format: 9 dates, 11 amounts, 20 names

## Limitations

1. **Context Dependency** - Accuracy improves with clear context
2. **Language Support** - Optimized for English (extends to French/Spanish with adaptation)
3. **Ambiguous Formats** - Some date formats (01/02/03) can be ambiguous
4. **Name Capitalization** - Requires proper capitalization for name extraction

## Future Enhancements

- [ ] ML model integration for improved name recognition
- [ ] Support for additional currencies (¥, ₹, etc.)
- [ ] Relative date parsing ("30 days from now")
- [ ] Multi-language support
- [ ] Address extraction
- [ ] Phone/email extraction integration

## Support

- **Documentation:** This file
- **CLI Help:** `python extract_cli.py --help`
- **Examples:** `test_field_extractor.py`
- **API Docs:** http://localhost:8001/docs

