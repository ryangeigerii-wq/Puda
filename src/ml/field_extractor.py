"""
Field Extractor - Second Core Capability for Puda AI

Specialized extractor for key document fields:
- Dates (various formats, relative dates, ranges)
- Amounts (currency, numbers, totals)
- Names (people, contacts, signatories)

Combines multiple extraction strategies:
1. Pattern-based extraction (regex)
2. ML model predictions (NER with BIO tags)
3. Context-aware validation
4. Confidence scoring
"""

import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import logging

try:
    from dateutil import parser as date_parser
    DATEUTIL_AVAILABLE = True
except ImportError:
    DATEUTIL_AVAILABLE = False

try:
    import phonenumbers
    PHONENUMBERS_AVAILABLE = True
except ImportError:
    PHONENUMBERS_AVAILABLE = False

logger = logging.getLogger(__name__)


class FieldExtractor:
    """
    Extract key fields from documents with high accuracy.
    
    Focuses on the most critical fields:
    - Dates (invoice dates, due dates, effective dates)
    - Amounts (totals, subtotals, taxes, payments)
    - Names (people, contacts, vendors, customers)
    """
    
    # Date patterns (various formats)
    DATE_PATTERNS = [
        # ISO format: 2024-01-15
        (r'\b(\d{4})-(\d{2})-(\d{2})\b', 'YYYY-MM-DD'),
        # US format: 01/15/2024, 1/15/24
        (r'\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b', 'MM/DD/YYYY'),
        # Written format: January 15, 2024
        (r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b', 'Month DD, YYYY'),
        # Short month: Jan 15, 2024
        (r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})\b', 'Mon DD, YYYY'),
        # European format: 15.01.2024, 15/01/2024
        (r'\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b', 'DD/MM/YYYY'),
        # Compact: 20240115
        (r'\b(20\d{2})(\d{2})(\d{2})\b', 'YYYYMMDD'),
    ]
    
    # Amount patterns (currency and numbers)
    AMOUNT_PATTERNS = [
        # $1,234.56 or $1234.56
        (r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', 'USD'),
        # 1,234.56 USD
        (r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*USD', 'USD'),
        # €1,234.56 or €1234.56
        (r'€\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', 'EUR'),
        # £1,234.56
        (r'£\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', 'GBP'),
        # Plain numbers with decimals: 1234.56
        (r'\b(\d{1,3}(?:,\d{3})+\.\d{2})\b', 'NUMBER'),
    ]
    
    # Name patterns and indicators
    NAME_INDICATORS = [
        'name:', 'contact:', 'attn:', 'attention:', 'from:', 'to:',
        'bill to:', 'ship to:', 'vendor:', 'customer:', 'client:',
        'prepared by:', 'authorized by:', 'signature:', 'signed:'
    ]
    
    # Amount context keywords
    AMOUNT_KEYWORDS = {
        'total': 10,      # High priority
        'amount': 9,
        'due': 8,
        'balance': 8,
        'subtotal': 7,
        'sum': 7,
        'payment': 6,
        'price': 5,
        'cost': 5,
        'tax': 4,
        'fee': 3,
    }
    
    def __init__(self):
        """Initialize field extractor."""
        self.compiled_date_patterns = [
            (re.compile(pattern, re.IGNORECASE), fmt)
            for pattern, fmt in self.DATE_PATTERNS
        ]
        
        self.compiled_amount_patterns = [
            (re.compile(pattern), currency)
            for pattern, currency in self.AMOUNT_PATTERNS
        ]
    
    def extract_dates(self, text: str, context_window: int = 50) -> List[Dict[str, Any]]:
        """
        Extract dates from text.
        
        Args:
            text: Document text
            context_window: Characters around match for context
            
        Returns:
            List of date dictionaries with text, normalized form, confidence, context
        """
        dates = []
        
        for pattern, fmt in self.compiled_date_patterns:
            for match in pattern.finditer(text):
                date_text = match.group(0)
                start, end = match.span()
                
                # Extract context
                context_start = max(0, start - context_window)
                context_end = min(len(text), end + context_window)
                context = text[context_start:context_end].strip()
                
                # Try to parse and normalize date
                normalized = self._normalize_date(date_text)
                
                # Determine confidence based on format and context
                confidence = self._date_confidence(date_text, context, fmt)
                
                dates.append({
                    'text': date_text,
                    'normalized': normalized,
                    'format': fmt,
                    'confidence': confidence,
                    'start': start,
                    'end': end,
                    'context': context,
                    'source': 'pattern'
                })
        
        # Deduplicate and sort by confidence
        dates = self._deduplicate_dates(dates)
        dates.sort(key=lambda x: x['confidence'], reverse=True)
        
        return dates
    
    def extract_amounts(self, text: str, context_window: int = 50) -> List[Dict[str, Any]]:
        """
        Extract monetary amounts from text.
        
        Args:
            text: Document text
            context_window: Characters around match for context
            
        Returns:
            List of amount dictionaries with text, value, currency, confidence, context
        """
        amounts = []
        
        for pattern, currency in self.compiled_amount_patterns:
            for match in pattern.finditer(text):
                amount_text = match.group(0)
                value_text = match.group(1)
                start, end = match.span()
                
                # Extract context
                context_start = max(0, start - context_window)
                context_end = min(len(text), end + context_window)
                context = text[context_start:context_end].strip()
                
                # Parse numeric value
                try:
                    value = float(value_text.replace(',', ''))
                except ValueError:
                    continue
                
                # Determine confidence based on context
                confidence = self._amount_confidence(amount_text, context, value)
                
                # Classify amount type from context
                amount_type = self._classify_amount_type(context)
                
                amounts.append({
                    'text': amount_text,
                    'value': value,
                    'currency': currency,
                    'type': amount_type,
                    'confidence': confidence,
                    'start': start,
                    'end': end,
                    'context': context,
                    'source': 'pattern'
                })
        
        # Deduplicate and sort by confidence
        amounts = self._deduplicate_amounts(amounts)
        amounts.sort(key=lambda x: x['confidence'], reverse=True)
        
        return amounts
    
    def extract_names(self, text: str, context_window: int = 50) -> List[Dict[str, Any]]:
        """
        Extract person names from text.
        
        Args:
            text: Document text
            context_window: Characters around match for context
            
        Returns:
            List of name dictionaries with text, confidence, context, role
        """
        names = []
        
        # Pattern 1: Names after indicators (Name: John Smith)
        for indicator in self.NAME_INDICATORS:
            pattern = re.compile(
                rf'{re.escape(indicator)}\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
                re.IGNORECASE
            )
            
            for match in pattern.finditer(text):
                name_text = match.group(1).strip()
                start, end = match.span(1)
                
                # Extract context
                context_start = max(0, start - context_window)
                context_end = min(len(text), end + context_window)
                context = text[context_start:context_end].strip()
                
                # Determine role from indicator
                role = self._classify_name_role(indicator, context)
                
                names.append({
                    'text': name_text,
                    'role': role,
                    'confidence': 0.85,  # High confidence with indicator
                    'start': start,
                    'end': end,
                    'context': context,
                    'source': 'pattern_indicator'
                })
        
        # Pattern 2: Capitalized names (John Smith, Jane Doe)
        # More conservative - requires 2-3 capitalized words
        pattern = re.compile(r'\b([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?)\b')
        
        for match in pattern.finditer(text):
            name_text = match.group(1).strip()
            start, end = match.span()
            
            # Skip if it looks like an organization or title
            if self._is_likely_organization(name_text, text[max(0, start-20):end+20]):
                continue
            
            # Extract context
            context_start = max(0, start - context_window)
            context_end = min(len(text), end + context_window)
            context = text[context_start:context_end].strip()
            
            # Lower confidence for names without indicators
            confidence = 0.65
            
            names.append({
                'text': name_text,
                'role': 'person',
                'confidence': confidence,
                'start': start,
                'end': end,
                'context': context,
                'source': 'pattern_capitalized'
            })
        
        # Deduplicate and sort by confidence
        names = self._deduplicate_names(names)
        names.sort(key=lambda x: x['confidence'], reverse=True)
        
        return names
    
    def extract_all(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract all fields at once.
        
        Args:
            text: Document text
            
        Returns:
            Dictionary with 'dates', 'amounts', 'names' keys
        """
        return {
            'dates': self.extract_dates(text),
            'amounts': self.extract_amounts(text),
            'names': self.extract_names(text),
        }
    
    def _normalize_date(self, date_text: str) -> Optional[str]:
        """Normalize date to ISO format (YYYY-MM-DD)."""
        if not DATEUTIL_AVAILABLE:
            return None
        
        try:
            dt = date_parser.parse(date_text, fuzzy=False)
            return dt.strftime('%Y-%m-%d')
        except:
            return None
    
    def _date_confidence(self, date_text: str, context: str, fmt: str) -> float:
        """Calculate confidence score for date extraction."""
        confidence = 0.70  # Base confidence
        
        # Boost for explicit date indicators
        date_keywords = ['date:', 'dated:', 'on:', 'effective:', 'expires:', 'due:', 'issued:']
        if any(kw in context.lower() for kw in date_keywords):
            confidence += 0.20
        
        # Boost for standard formats
        if fmt in ['YYYY-MM-DD', 'MM/DD/YYYY']:
            confidence += 0.05
        
        # Cap at 0.95
        return min(confidence, 0.95)
    
    def _amount_confidence(self, amount_text: str, context: str, value: float) -> float:
        """Calculate confidence score for amount extraction."""
        confidence = 0.70  # Base confidence
        
        # Boost based on context keywords
        context_lower = context.lower()
        for keyword, priority in self.AMOUNT_KEYWORDS.items():
            if keyword in context_lower:
                confidence += priority * 0.02
                break
        
        # Boost for currency symbols
        if any(symbol in amount_text for symbol in ['$', '€', '£']):
            confidence += 0.10
        
        # Reduce for very small or very large amounts (likely errors)
        if value < 0.01 or value > 1000000000:
            confidence -= 0.20
        
        # Cap at 0.95
        return min(max(confidence, 0.30), 0.95)
    
    def _classify_amount_type(self, context: str) -> str:
        """Classify amount type from context."""
        context_lower = context.lower()
        
        if 'total' in context_lower:
            return 'total'
        elif 'subtotal' in context_lower or 'sub-total' in context_lower:
            return 'subtotal'
        elif 'tax' in context_lower:
            return 'tax'
        elif 'due' in context_lower or 'balance' in context_lower:
            return 'amount_due'
        elif 'payment' in context_lower or 'paid' in context_lower:
            return 'payment'
        elif 'discount' in context_lower:
            return 'discount'
        else:
            return 'amount'
    
    def _classify_name_role(self, indicator: str, context: str) -> str:
        """Classify name role from indicator and context."""
        indicator_lower = indicator.lower()
        context_lower = context.lower()
        
        if 'vendor' in indicator_lower or 'seller' in indicator_lower:
            return 'vendor'
        elif 'customer' in indicator_lower or 'client' in indicator_lower or 'bill to' in indicator_lower:
            return 'customer'
        elif 'contact' in indicator_lower or 'attn' in indicator_lower:
            return 'contact'
        elif 'authorized' in indicator_lower or 'signed' in indicator_lower or 'signature' in indicator_lower:
            return 'signatory'
        elif 'prepared' in indicator_lower:
            return 'preparer'
        else:
            return 'person'
    
    def _is_likely_organization(self, name_text: str, context: str) -> bool:
        """Check if capitalized text is likely an organization, not a person."""
        org_indicators = [
            'inc', 'corp', 'corporation', 'llc', 'ltd', 'limited',
            'company', 'co.', 'group', 'association', 'foundation',
            'institute', 'university', 'college', 'department'
        ]
        
        name_lower = name_text.lower()
        context_lower = context.lower()
        
        # Check for org suffixes
        for indicator in org_indicators:
            if indicator in name_lower or indicator in context_lower:
                return True
        
        # Check if all words are capitalized (unusual for person names)
        words = name_text.split()
        if len(words) > 2 and all(w[0].isupper() and w[1:].isupper() for w in words if len(w) > 1):
            return True
        
        return False
    
    def _deduplicate_dates(self, dates: List[Dict]) -> List[Dict]:
        """Remove duplicate date extractions."""
        seen = set()
        unique = []
        
        for date in dates:
            # Use normalized date or text as key
            key = date.get('normalized') or date['text']
            if key not in seen:
                seen.add(key)
                unique.append(date)
        
        return unique
    
    def _deduplicate_amounts(self, amounts: List[Dict]) -> List[Dict]:
        """Remove duplicate amount extractions."""
        seen = set()
        unique = []
        
        for amount in amounts:
            # Use value as key
            key = amount['value']
            if key not in seen:
                seen.add(key)
                unique.append(amount)
        
        return unique
    
    def _deduplicate_names(self, names: List[Dict]) -> List[Dict]:
        """Remove duplicate name extractions."""
        seen = set()
        unique = []
        
        for name in names:
            # Normalize and use as key
            key = name['text'].lower().strip()
            if key not in seen:
                seen.add(key)
                unique.append(name)
        
        return unique


# Convenience function
def extract_fields(text: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Quick field extraction.
    
    Args:
        text: Document text
        
    Returns:
        Dictionary with dates, amounts, and names
    """
    extractor = FieldExtractor()
    return extractor.extract_all(text)


# Example usage
if __name__ == "__main__":
    sample_text = """
    ACME Corporation
    Invoice #INV-2024-12345
    
    Date: January 15, 2024
    Due Date: February 15, 2024
    
    Bill To:
    John Smith
    Tech Solutions Inc.
    456 Tech Drive
    San Francisco, CA 94102
    
    Description                     Amount
    Consulting Services           $6,000.00
    Software License                $500.00
    Support & Maintenance           $600.00
    
    Subtotal:                     $7,100.00
    Tax (8.5%):                     $603.50
    Total Amount Due:             $7,703.50
    
    Payment Terms: Net 30
    
    Authorized by: Jane Doe
    Date: 2024-01-15
    """
    
    print("Field Extraction Example")
    print("=" * 70)
    
    extractor = FieldExtractor()
    results = extractor.extract_all(sample_text)
    
    print("\nDates Found:")
    for date in results['dates'][:5]:
        print(f"  {date['text']} → {date['normalized']} "
              f"(confidence: {date['confidence']:.2f})")
    
    print("\nAmounts Found:")
    for amount in results['amounts'][:5]:
        print(f"  {amount['text']} = ${amount['value']:,.2f} "
              f"({amount['type']}, confidence: {amount['confidence']:.2f})")
    
    print("\nNames Found:")
    for name in results['names'][:5]:
        print(f"  {name['text']} ({name['role']}, "
              f"confidence: {name['confidence']:.2f})")
