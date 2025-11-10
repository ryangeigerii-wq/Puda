"""
Document Summarizer - Third Core Capability

Generates concise summaries of documents using extractive and abstractive methods.
Focuses on key sentences, main points, and overall document meaning.

Features:
- Extractive summarization (selects important sentences)
- Abstractive summarization (generates new concise text)
- Configurable summary length (short, medium, long)
- Multi-paragraph support
- Confidence scoring for summary quality
- Bullet point extraction
- Key statistics (word count, sentence count, reduction ratio)
"""

import re
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from collections import Counter
import math


@dataclass
class SummaryResult:
    """Result from document summarization."""
    summary: str
    method: str  # 'extractive', 'abstractive', 'hybrid'
    length: str  # 'short', 'medium', 'long'
    confidence: float
    original_length: int  # character count
    summary_length: int  # character count
    reduction_ratio: float  # percentage reduction
    key_sentences: List[str]
    bullet_points: List[str]
    statistics: Dict


class DocumentSummarizer:
    """
    Document summarization using extractive and abstractive methods.
    
    Extractive: Selects the most important sentences from the document.
    Abstractive: Generates a new summary by paraphrasing key points.
    Hybrid: Combines both approaches for best results.
    """
    
    def __init__(self):
        """Initialize the summarizer."""
        # Keywords that indicate important sentences
        self.importance_keywords = {
            'conclusion', 'summary', 'total', 'amount', 'due', 'important',
            'key', 'main', 'significant', 'critical', 'essential', 'required',
            'must', 'shall', 'agreement', 'contract', 'invoice', 'payment',
            'deadline', 'date', 'effective', 'expiration', 'notice', 'terms'
        }
        
        # Document type indicators for context-aware summarization
        self.doc_type_patterns = {
            'invoice': ['invoice', 'bill', 'payment', 'amount due'],
            'contract': ['agreement', 'party', 'term', 'condition', 'whereas'],
            'receipt': ['receipt', 'purchase', 'transaction', 'paid'],
            'letter': ['dear', 'sincerely', 'regards', 'correspondence'],
            'report': ['report', 'analysis', 'findings', 'results', 'conclusion'],
            'memo': ['memo', 'memorandum', 'to:', 'from:', 'subject:']
        }
        
        # Stop words for TF-IDF calculation
        self.stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'will', 'with', 'the', 'this', 'but', 'they', 'have',
            'had', 'what', 'when', 'where', 'who', 'which', 'why', 'how'
        }
    
    def summarize(
        self,
        text: str,
        method: str = 'extractive',
        length: str = 'medium',
        max_sentences: Optional[int] = None,
        include_bullets: bool = True
    ) -> SummaryResult:
        """
        Summarize a document.
        
        Args:
            text: Document text to summarize
            method: 'extractive', 'abstractive', or 'hybrid'
            length: 'short' (1-2 sentences), 'medium' (3-5), 'long' (5-8)
            max_sentences: Override automatic sentence count
            include_bullets: Extract bullet points if available
            
        Returns:
            SummaryResult with summary and metadata
        """
        if not text or not text.strip():
            return self._empty_result()
        
        # Detect document type for context
        doc_type = self._detect_document_type(text)
        
        # Extract sentences
        sentences = self._split_sentences(text)
        
        if len(sentences) == 0:
            return self._empty_result()
        
        # Determine target sentence count
        if max_sentences is not None:
            target_count = max_sentences
        else:
            target_count = self._get_target_sentence_count(length, len(sentences))
        
        # Choose summarization method
        if method == 'extractive':
            summary_text, key_sentences = self._extractive_summarize(
                text, sentences, target_count, doc_type
            )
            confidence = self._calculate_extractive_confidence(
                sentences, key_sentences
            )
        elif method == 'abstractive':
            summary_text, key_sentences = self._abstractive_summarize(
                text, sentences, target_count, doc_type
            )
            confidence = self._calculate_abstractive_confidence(text, summary_text)
        else:  # hybrid
            summary_text, key_sentences = self._hybrid_summarize(
                text, sentences, target_count, doc_type
            )
            confidence = (
                self._calculate_extractive_confidence(sentences, key_sentences) * 0.6 +
                self._calculate_abstractive_confidence(text, summary_text) * 0.4
            )
        
        # Extract bullet points if requested
        bullet_points = []
        if include_bullets:
            bullet_points = self._extract_bullet_points(text)
        
        # Calculate statistics
        original_length = len(text)
        summary_length = len(summary_text)
        reduction_ratio = (1 - summary_length / original_length) * 100 if original_length > 0 else 0
        
        statistics = {
            'original_words': len(text.split()),
            'summary_words': len(summary_text.split()),
            'original_sentences': len(sentences),
            'summary_sentences': len(key_sentences),
            'document_type': doc_type,
            'reduction_ratio': round(reduction_ratio, 1)
        }
        
        return SummaryResult(
            summary=summary_text,
            method=method,
            length=length,
            confidence=confidence,
            original_length=original_length,
            summary_length=summary_length,
            reduction_ratio=reduction_ratio,
            key_sentences=key_sentences,
            bullet_points=bullet_points,
            statistics=statistics
        )
    
    def summarize_batch(
        self,
        documents: List[str],
        method: str = 'extractive',
        length: str = 'medium'
    ) -> List[SummaryResult]:
        """
        Summarize multiple documents.
        
        Args:
            documents: List of document texts
            method: Summarization method
            length: Summary length
            
        Returns:
            List of SummaryResult objects
        """
        return [
            self.summarize(doc, method=method, length=length)
            for doc in documents
        ]
    
    def _extractive_summarize(
        self,
        text: str,
        sentences: List[str],
        target_count: int,
        doc_type: str
    ) -> Tuple[str, List[str]]:
        """
        Extractive summarization: select most important sentences.
        
        Uses TF-IDF scoring combined with position and keyword importance.
        """
        if len(sentences) <= target_count:
            return text.strip(), sentences
        
        # Score each sentence
        sentence_scores = []
        for i, sentence in enumerate(sentences):
            score = self._score_sentence(sentence, i, len(sentences), sentences, doc_type)
            sentence_scores.append((score, i, sentence))
        
        # Select top sentences, maintaining original order
        sentence_scores.sort(reverse=True)
        selected_indices = sorted([idx for _, idx, _ in sentence_scores[:target_count]])
        selected_sentences = [sentences[i] for i in selected_indices]
        
        summary = ' '.join(selected_sentences)
        return summary, selected_sentences
    
    def _abstractive_summarize(
        self,
        text: str,
        sentences: List[str],
        target_count: int,
        doc_type: str
    ) -> Tuple[str, List[str]]:
        """
        Abstractive summarization: generate new concise text.
        
        Since we don't have a transformer model yet, we use a template-based
        approach that extracts key information and reformats it concisely.
        """
        # First, get key sentences via extractive method
        _, key_sentences = self._extractive_summarize(
            text, sentences, min(target_count + 2, len(sentences)), doc_type
        )
        
        # Extract key information
        doc_info = self._extract_document_info(text, doc_type)
        
        # Generate abstractive summary based on document type
        if doc_type == 'invoice':
            summary = self._generate_invoice_summary(doc_info)
        elif doc_type == 'contract':
            summary = self._generate_contract_summary(doc_info)
        elif doc_type == 'receipt':
            summary = self._generate_receipt_summary(doc_info)
        elif doc_type == 'letter':
            summary = self._generate_letter_summary(doc_info, key_sentences)
        elif doc_type == 'report':
            summary = self._generate_report_summary(doc_info, key_sentences)
        else:
            # Generic summary: compress key sentences
            summary = self._compress_sentences(key_sentences, target_count)
        
        return summary, key_sentences
    
    def _hybrid_summarize(
        self,
        text: str,
        sentences: List[str],
        target_count: int,
        doc_type: str
    ) -> Tuple[str, List[str]]:
        """
        Hybrid summarization: combine extractive and abstractive.
        
        Uses extractive to find key content, then abstractive to compress.
        """
        # Get extractive summary with more sentences
        extractive_count = min(target_count + 3, len(sentences))
        _, key_sentences = self._extractive_summarize(
            text, sentences, extractive_count, doc_type
        )
        
        # Apply abstractive compression
        doc_info = self._extract_document_info(text, doc_type)
        
        if doc_type in ['invoice', 'receipt', 'contract']:
            # Use structured summary for structured documents
            summary, _ = self._abstractive_summarize(text, sentences, target_count, doc_type)
        else:
            # Compress extractive sentences
            summary = self._compress_sentences(key_sentences, target_count)
        
        return summary, key_sentences
    
    def _score_sentence(
        self,
        sentence: str,
        position: int,
        total: int,
        all_sentences: List[str],
        doc_type: str
    ) -> float:
        """
        Score a sentence for importance using multiple factors.
        """
        score = 0.0
        sentence_lower = sentence.lower()
        
        # 1. Position score (first and last sentences are often important)
        if position == 0:
            score += 0.3  # First sentence bonus
        elif position == total - 1:
            score += 0.2  # Last sentence bonus
        elif position < 3:
            score += 0.15  # Early sentence bonus
        
        # 2. Length score (prefer medium-length sentences)
        word_count = len(sentence.split())
        if 10 <= word_count <= 30:
            score += 0.2
        elif word_count < 5:
            score -= 0.1  # Penalize very short sentences
        
        # 3. Keyword importance
        for keyword in self.importance_keywords:
            if keyword in sentence_lower:
                score += 0.15
        
        # 4. Document type specific keywords
        if doc_type in self.doc_type_patterns:
            for pattern in self.doc_type_patterns[doc_type]:
                if pattern in sentence_lower:
                    score += 0.1
        
        # 5. TF-IDF score
        tfidf_score = self._calculate_tfidf_score(sentence, all_sentences)
        score += tfidf_score * 0.3
        
        # 6. Numerical content (dates, amounts often important)
        if re.search(r'\d+', sentence):
            score += 0.1
        
        # 7. Proper nouns (capitalized words, often important)
        proper_nouns = len([w for w in sentence.split() if w and w[0].isupper()])
        score += min(proper_nouns * 0.05, 0.2)
        
        return score
    
    def _calculate_tfidf_score(self, sentence: str, all_sentences: List[str]) -> float:
        """Calculate TF-IDF based importance score."""
        words = [w.lower() for w in sentence.split() if w.lower() not in self.stop_words]
        
        if not words:
            return 0.0
        
        # Term frequency in this sentence
        tf = Counter(words)
        
        # Document frequency across all sentences
        df = {}
        for sent in all_sentences:
            sent_words = set(w.lower() for w in sent.split() if w.lower() not in self.stop_words)
            for word in sent_words:
                df[word] = df.get(word, 0) + 1
        
        # Calculate TF-IDF score
        tfidf_sum = 0.0
        for word, count in tf.items():
            tf_score = count / len(words)
            idf_score = math.log(len(all_sentences) / (df.get(word, 1) + 1))
            tfidf_sum += tf_score * idf_score
        
        return tfidf_sum / len(words) if words else 0.0
    
    def _extract_document_info(self, text: str, doc_type: str) -> Dict:
        """Extract key information from document for abstractive summary."""
        info = {
            'doc_type': doc_type,
            'dates': [],
            'amounts': [],
            'names': [],
            'key_terms': []
        }
        
        # Extract dates
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # ISO
            r'\d{1,2}/\d{1,2}/\d{4}',  # US
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b'  # Written
        ]
        for pattern in date_patterns:
            info['dates'].extend(re.findall(pattern, text, re.IGNORECASE))
        
        # Extract amounts
        amount_patterns = [
            r'\$[\d,]+\.?\d*',  # Dollar
            r'€[\d,]+\.?\d*',  # Euro
            r'£[\d,]+\.?\d*',  # Pound
        ]
        for pattern in amount_patterns:
            info['amounts'].extend(re.findall(pattern, text))
        
        # Extract capitalized phrases (likely names/entities)
        capitalized = re.findall(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', text)
        info['names'] = list(set(capitalized))[:5]  # Top 5 unique names
        
        # Extract key terms (frequent important words)
        words = [w.lower() for w in text.split() if w.lower() not in self.stop_words and len(w) > 4]
        word_freq = Counter(words)
        info['key_terms'] = [word for word, _ in word_freq.most_common(10)]
        
        return info
    
    def _generate_invoice_summary(self, info: Dict) -> str:
        """Generate summary for invoice documents."""
        parts = ["Invoice"]
        
        if info['dates']:
            parts.append(f"dated {info['dates'][0]}")
        
        if info['amounts']:
            # Get the largest amount (likely the total)
            amounts = [self._parse_amount(a) for a in info['amounts']]
            max_amount = max(amounts) if amounts else None
            if max_amount:
                parts.append(f"for {self._format_amount(max_amount)}")
        
        if info['names']:
            parts.append(f"to/from {info['names'][0]}")
        
        summary = ' '.join(parts) + '.'
        
        # Add payment terms if found
        if any(term in info['key_terms'] for term in ['payment', 'due', 'terms']):
            summary += " Payment terms and details included."
        
        return summary
    
    def _generate_contract_summary(self, info: Dict) -> str:
        """Generate summary for contract documents."""
        parts = ["Contract"]
        
        if info['names']:
            if len(info['names']) >= 2:
                parts.append(f"between {info['names'][0]} and {info['names'][1]}")
            else:
                parts.append(f"involving {info['names'][0]}")
        
        if info['dates']:
            parts.append(f"effective {info['dates'][0]}")
        
        summary = ' '.join(parts) + '.'
        
        # Add terms mention
        if 'term' in info['key_terms'] or 'condition' in info['key_terms']:
            summary += " Terms and conditions specified."
        
        if info['amounts']:
            summary += f" Financial terms: {info['amounts'][0]}."
        
        return summary
    
    def _generate_receipt_summary(self, info: Dict) -> str:
        """Generate summary for receipt documents."""
        parts = ["Receipt"]
        
        if info['dates']:
            parts.append(f"from {info['dates'][0]}")
        
        if info['amounts']:
            # Total is usually the largest or last amount
            parts.append(f"for {info['amounts'][-1]}")
        
        summary = ' '.join(parts) + '.'
        
        if len(info['amounts']) > 1:
            summary += f" {len(info['amounts'])} line items."
        
        return summary
    
    def _generate_letter_summary(self, info: Dict, key_sentences: List[str]) -> str:
        """Generate summary for letter documents."""
        # Use first key sentence as main point
        if key_sentences:
            main_point = key_sentences[0]
            # Truncate if too long
            if len(main_point) > 150:
                main_point = main_point[:147] + '...'
            summary = f"Letter: {main_point}"
        else:
            summary = "Correspondence"
        
        if info['names']:
            summary += f" From/To: {info['names'][0]}."
        
        return summary
    
    def _generate_report_summary(self, info: Dict, key_sentences: List[str]) -> str:
        """Generate summary for report documents."""
        if key_sentences:
            # Use last key sentence (often contains conclusion)
            conclusion = key_sentences[-1]
            if len(conclusion) > 150:
                conclusion = conclusion[:147] + '...'
            summary = f"Report: {conclusion}"
        else:
            summary = "Report with findings and analysis"
        
        if 'conclusion' in info['key_terms'] or 'result' in info['key_terms']:
            summary += " Includes conclusions."
        
        return summary
    
    def _compress_sentences(self, sentences: List[str], target_count: int) -> str:
        """Compress sentences by selecting most important ones."""
        if len(sentences) <= target_count:
            return ' '.join(sentences)
        
        # Score sentences by length and content
        scored = []
        for sent in sentences:
            score = len(sent.split())  # Prefer longer sentences
            if any(kw in sent.lower() for kw in self.importance_keywords):
                score += 20
            scored.append((score, sent))
        
        scored.sort(reverse=True)
        selected = [sent for _, sent in scored[:target_count]]
        
        return ' '.join(selected)
    
    def _parse_amount(self, amount_str: str) -> float:
        """Parse amount string to numeric value."""
        try:
            # Remove currency symbols and commas
            clean = re.sub(r'[$€£,]', '', amount_str)
            return float(clean)
        except:
            return 0.0
    
    def _format_amount(self, amount: float) -> str:
        """Format amount with currency symbol."""
        return f"${amount:,.2f}"
    
    def _extract_bullet_points(self, text: str) -> List[str]:
        """Extract bullet points or numbered lists from text."""
        bullets = []
        
        # Match bullet points (•, -, *, etc.)
        bullet_pattern = r'^[\s]*[•\-\*]\s+(.+)$'
        bullets.extend(re.findall(bullet_pattern, text, re.MULTILINE))
        
        # Match numbered lists (1. 2. etc.)
        numbered_pattern = r'^[\s]*\d+[\.\)]\s+(.+)$'
        bullets.extend(re.findall(numbered_pattern, text, re.MULTILINE))
        
        return bullets[:10]  # Limit to 10 bullet points
    
    def _detect_document_type(self, text: str) -> str:
        """Detect document type from content."""
        text_lower = text.lower()
        
        scores = {}
        for doc_type, patterns in self.doc_type_patterns.items():
            score = sum(1 for pattern in patterns if pattern in text_lower)
            if score > 0:
                scores[doc_type] = score
        
        if scores:
            return max(scores, key=scores.get)
        
        return 'document'
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        # Handle common abbreviations to avoid false splits
        text = re.sub(r'\b(Mr|Mrs|Ms|Dr|Prof|Inc|Ltd|Corp)\.\s', r'\1<DOT> ', text)
        
        # Split on . ! ? followed by space and capital letter
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        
        # Restore abbreviations
        sentences = [s.replace('<DOT>', '.') for s in sentences]
        
        # Clean and filter
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _get_target_sentence_count(self, length: str, total_sentences: int) -> int:
        """Determine target number of sentences for summary."""
        if length == 'short':
            base = 2
        elif length == 'medium':
            base = 4
        else:  # long
            base = 6
        
        # Adjust based on document length
        if total_sentences < 5:
            return min(2, total_sentences)
        elif total_sentences < 10:
            return min(base, total_sentences)
        else:
            return min(base + 2, max(base, int(total_sentences * 0.3)))
    
    def _calculate_extractive_confidence(
        self,
        all_sentences: List[str],
        selected_sentences: List[str]
    ) -> float:
        """Calculate confidence score for extractive summary."""
        if not selected_sentences:
            return 0.0
        
        # Base confidence on coverage and sentence quality
        coverage = len(selected_sentences) / len(all_sentences) if all_sentences else 0
        
        # Check if selected sentences contain important keywords
        keyword_matches = sum(
            1 for sent in selected_sentences
            if any(kw in sent.lower() for kw in self.importance_keywords)
        )
        keyword_ratio = keyword_matches / len(selected_sentences)
        
        # Combine factors
        confidence = 0.5 + (keyword_ratio * 0.3) + (min(coverage, 0.5) * 0.2)
        
        return min(confidence, 0.95)
    
    def _calculate_abstractive_confidence(self, original: str, summary: str) -> float:
        """Calculate confidence score for abstractive summary."""
        if not summary:
            return 0.0
        
        # Check compression ratio (should be significant but not too extreme)
        ratio = len(summary) / len(original) if original else 0
        
        if 0.1 <= ratio <= 0.4:  # Good compression
            ratio_score = 0.9
        elif 0.05 <= ratio <= 0.6:  # Acceptable compression
            ratio_score = 0.7
        else:  # Too much or too little compression
            ratio_score = 0.5
        
        # Check if key information is preserved
        key_words = set(w.lower() for w in original.split() if len(w) > 5)
        summary_words = set(w.lower() for w in summary.split())
        
        preservation = len(key_words & summary_words) / len(key_words) if key_words else 0.5
        
        confidence = ratio_score * 0.6 + preservation * 0.4
        
        return min(confidence, 0.95)
    
    def _empty_result(self) -> SummaryResult:
        """Return empty result for invalid input."""
        return SummaryResult(
            summary="",
            method="none",
            length="short",
            confidence=0.0,
            original_length=0,
            summary_length=0,
            reduction_ratio=0.0,
            key_sentences=[],
            bullet_points=[],
            statistics={
                'original_words': 0,
                'summary_words': 0,
                'original_sentences': 0,
                'summary_sentences': 0,
                'document_type': 'unknown',
                'reduction_ratio': 0.0
            }
        )


# Convenience function for quick summarization
def summarize_text(
    text: str,
    method: str = 'extractive',
    length: str = 'medium'
) -> str:
    """
    Quick summarization function.
    
    Args:
        text: Document text
        method: 'extractive', 'abstractive', or 'hybrid'
        length: 'short', 'medium', or 'long'
        
    Returns:
        Summary text
    """
    summarizer = DocumentSummarizer()
    result = summarizer.summarize(text, method=method, length=length)
    return result.summary
