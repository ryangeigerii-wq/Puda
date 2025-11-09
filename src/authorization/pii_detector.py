"""
PII Detector - Personal Identifiable Information Detection

Detects PII in text and automatically escalates document confidentiality level.
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class PIIType(Enum):
    """Types of PII that can be detected."""
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    PHONE = "phone"
    EMAIL = "email"
    IP_ADDRESS = "ip_address"
    DATE_OF_BIRTH = "date_of_birth"
    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"


@dataclass
class PIIMatch:
    """
    A detected PII match.
    
    Attributes:
        pii_type: Type of PII detected
        value: Matched value (partially redacted)
        position: Position in text (start, end)
        confidence: Confidence score (0-1)
    """
    pii_type: PIIType
    value: str
    position: tuple
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'pii_type': self.pii_type.value,
            'value': self.value,
            'position': self.position,
            'confidence': self.confidence
        }


class PIIDetector:
    """
    Detect Personal Identifiable Information (PII) in text.
    
    Features:
    - Pattern-based detection using regex
    - Multiple PII types (SSN, credit cards, phone, email, etc.)
    - Confidence scoring
    - Automatic confidentiality escalation
    """
    
    def __init__(self):
        """Initialize PII detector with patterns."""
        self.patterns = self._load_patterns()
    
    def _load_patterns(self) -> Dict[PIIType, List[re.Pattern]]:
        """
        Load regex patterns for PII detection.
        
        Returns:
            Dictionary mapping PII types to regex patterns
        """
        patterns = {
            # Social Security Number (SSN)
            # Format: XXX-XX-XXXX or XXX XX XXXX or XXXXXXXXX
            PIIType.SSN: [
                re.compile(r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b'),
            ],
            
            # Credit Card Numbers
            # Visa, MasterCard, Amex, Discover
            PIIType.CREDIT_CARD: [
                re.compile(r'\b(?:4\d{3}|5[1-5]\d{2}|6(?:011|5\d{2})|3[47]\d{2})[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
                re.compile(r'\b(?:4\d{12}(?:\d{3})?|5[1-5]\d{14}|3[47]\d{13})\b'),
            ],
            
            # Phone Numbers
            # US format: (123) 456-7890, 123-456-7890, 123.456.7890, 1234567890
            PIIType.PHONE: [
                re.compile(r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
                re.compile(r'\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b'),
            ],
            
            # Email Addresses
            PIIType.EMAIL: [
                re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            ],
            
            # IP Addresses
            PIIType.IP_ADDRESS: [
                re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
            ],
            
            # Date of Birth
            # Formats: MM/DD/YYYY, MM-DD-YYYY, YYYY-MM-DD
            PIIType.DATE_OF_BIRTH: [
                re.compile(r'\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b'),
                re.compile(r'\b(?:19|20)\d{2}[/-](?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])\b'),
            ],
            
            # Passport Numbers (simplified - US format)
            PIIType.PASSPORT: [
                re.compile(r'\b[A-Z]{1,2}\d{6,9}\b'),
            ],
            
            # Driver's License (simplified - varies by state)
            PIIType.DRIVERS_LICENSE: [
                re.compile(r'\b[A-Z]\d{7,8}\b'),  # Many states use this format
            ],
        }
        
        return patterns
    
    def detect(self, text: str) -> List[PIIMatch]:
        """
        Detect PII in text.
        
        Args:
            text: Text to scan for PII
            
        Returns:
            List of PIIMatch objects
        """
        if not text:
            return []
        
        matches = []
        
        for pii_type, pattern_list in self.patterns.items():
            for pattern in pattern_list:
                for match in pattern.finditer(text):
                    # Validate match (basic checks)
                    if self._validate_match(pii_type, match.group()):
                        matches.append(PIIMatch(
                            pii_type=pii_type,
                            value=self._redact_value(match.group()),
                            position=(match.start(), match.end()),
                            confidence=self._calculate_confidence(pii_type, match.group())
                        ))
        
        return matches
    
    def _validate_match(self, pii_type: PIIType, value: str) -> bool:
        """
        Validate detected match to reduce false positives.
        
        Args:
            pii_type: Type of PII
            value: Matched value
            
        Returns:
            True if valid match
        """
        if pii_type == PIIType.CREDIT_CARD:
            # Luhn algorithm check
            return self._luhn_check(value.replace('-', '').replace(' ', ''))
        
        elif pii_type == PIIType.SSN:
            # Basic SSN validation
            digits = value.replace('-', '').replace(' ', '')
            if len(digits) != 9:
                return False
            # Invalid SSN patterns
            if digits[0:3] == '000' or digits[3:5] == '00' or digits[5:9] == '0000':
                return False
            if digits[0:3] == '666' or int(digits[0:3]) >= 900:
                return False
            return True
        
        elif pii_type == PIIType.EMAIL:
            # More strict email validation
            return '@' in value and '.' in value.split('@')[1]
        
        elif pii_type == PIIType.IP_ADDRESS:
            # Validate IP address octets
            parts = value.split('.')
            if len(parts) != 4:
                return False
            try:
                return all(0 <= int(p) <= 255 for p in parts)
            except ValueError:
                return False
        
        # Other types pass basic regex validation
        return True
    
    def _luhn_check(self, card_number: str) -> bool:
        """
        Validate credit card using Luhn algorithm.
        
        Args:
            card_number: Card number string (digits only)
            
        Returns:
            True if valid per Luhn algorithm
        """
        if not card_number.isdigit():
            return False
        
        digits = [int(d) for d in card_number]
        checksum = 0
        
        # Process digits from right to left
        for i, digit in enumerate(reversed(digits)):
            if i % 2 == 1:  # Every second digit from right
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit
        
        return checksum % 10 == 0
    
    def _calculate_confidence(self, pii_type: PIIType, value: str) -> float:
        """
        Calculate confidence score for match.
        
        Args:
            pii_type: Type of PII
            value: Matched value
            
        Returns:
            Confidence score (0-1)
        """
        # Base confidence
        confidence = 0.8
        
        # Adjust based on type and characteristics
        if pii_type == PIIType.CREDIT_CARD:
            # Higher confidence for validated Luhn
            confidence = 0.95
        elif pii_type == PIIType.SSN:
            # High confidence for validated SSN
            confidence = 0.9
        elif pii_type == PIIType.EMAIL:
            # Reasonable confidence for email
            confidence = 0.85
        elif pii_type == PIIType.PHONE:
            # Medium confidence (many false positives possible)
            confidence = 0.7
        elif pii_type == PIIType.DATE_OF_BIRTH:
            # Lower confidence (dates could be other things)
            confidence = 0.6
        
        return confidence
    
    def _redact_value(self, value: str) -> str:
        """
        Redact PII value for logging/display.
        
        Args:
            value: Original PII value
            
        Returns:
            Partially redacted value
        """
        if len(value) <= 4:
            return '*' * len(value)
        
        # Show first 2 and last 2 characters
        return value[:2] + '*' * (len(value) - 4) + value[-2:]
    
    def scan_document(
        self,
        document: Dict[str, Any],
        text_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Scan document for PII and escalate confidentiality if found.
        
        Args:
            document: Document dictionary
            text_fields: List of fields to scan (default: ['ocr_text', 'extracted_text'])
            
        Returns:
            Dictionary with PII scan results
        """
        if text_fields is None:
            text_fields = ['ocr_text', 'extracted_text', 'text']
        
        all_matches = []
        
        # Scan specified text fields
        for field in text_fields:
            if field in document and document[field]:
                matches = self.detect(str(document[field]))
                all_matches.extend(matches)
        
        # Determine if escalation needed
        has_pii = len(all_matches) > 0
        high_confidence_pii = [m for m in all_matches if m.confidence >= 0.8]
        
        result = {
            'has_pii': has_pii,
            'pii_count': len(all_matches),
            'high_confidence_count': len(high_confidence_pii),
            'pii_types': list(set(m.pii_type.value for m in all_matches)),
            'matches': [m.to_dict() for m in all_matches],
            'escalated': False,
            'original_confidentiality': document.get('confidentiality_level', 1)
        }
        
        # Escalate if high-confidence PII found
        if high_confidence_pii:
            current_level = document.get('confidentiality_level', 1)
            # Escalate to at least CONFIDENTIAL (2)
            new_level = max(current_level, 2)
            
            if new_level > current_level:
                document['confidentiality_level'] = new_level
                document['pii_detected'] = True
                document['pii_types'] = result['pii_types']
                result['escalated'] = True
                result['new_confidentiality'] = new_level
        
        return result
    
    def redact_pii(self, text: str, replacement: str = "[REDACTED]") -> str:
        """
        Redact PII from text.
        
        Args:
            text: Original text
            replacement: Replacement string for PII
            
        Returns:
            Text with PII redacted
        """
        if not text:
            return text
        
        matches = self.detect(text)
        
        # Sort matches by position (descending) to replace from end to start
        matches.sort(key=lambda m: m.position[0], reverse=True)
        
        redacted_text = text
        for match in matches:
            start, end = match.position
            redacted_text = redacted_text[:start] + replacement + redacted_text[end:]
        
        return redacted_text
