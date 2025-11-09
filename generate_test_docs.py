"""
Generate synthetic document images for testing OCR pipeline.
Creates sample invoices, receipts, and contracts with multilingual text.
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentGenerator:
    """Generate synthetic document images for testing."""
    
    def __init__(self, output_dir: str = "data/test_documents"):
        """
        Initialize document generator.
        
        Args:
            output_dir: Directory to save generated images
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Document dimensions (letter size at 300 DPI)
        self.width = 2550  # 8.5 inches * 300 DPI
        self.height = 3300  # 11 inches * 300 DPI
        
        # Try to load fonts, fall back to default
        try:
            self.font_large = ImageFont.truetype("arial.ttf", 60)
            self.font_medium = ImageFont.truetype("arial.ttf", 40)
            self.font_small = ImageFont.truetype("arial.ttf", 30)
        except:
            logger.warning("Arial font not found, using default font")
            self.font_large = ImageFont.load_default()
            self.font_medium = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
    
    def generate_invoice_english(self) -> str:
        """Generate English invoice."""
        img = Image.new('RGB', (self.width, self.height), 'white')
        draw = ImageDraw.Draw(img)
        
        y = 100
        
        # Header
        draw.text((100, y), "INVOICE", fill='black', font=self.font_large)
        y += 120
        
        # Company info
        draw.text((100, y), "ACME Corporation", fill='black', font=self.font_medium)
        y += 60
        draw.text((100, y), "123 Business Street", fill='black', font=self.font_small)
        y += 50
        draw.text((100, y), "New York, NY 10001", fill='black', font=self.font_small)
        y += 100
        
        # Invoice details
        draw.text((100, y), "Invoice Number: INV-2025-001", fill='black', font=self.font_small)
        y += 60
        draw.text((100, y), "Date: November 8, 2025", fill='black', font=self.font_small)
        y += 60
        draw.text((100, y), "Due Date: December 8, 2025", fill='black', font=self.font_small)
        y += 100
        
        # Bill to
        draw.text((100, y), "Bill To:", fill='black', font=self.font_medium)
        y += 60
        draw.text((100, y), "John Smith", fill='black', font=self.font_small)
        y += 50
        draw.text((100, y), "456 Customer Ave", fill='black', font=self.font_small)
        y += 50
        draw.text((100, y), "Los Angeles, CA 90001", fill='black', font=self.font_small)
        y += 100
        
        # Line items
        draw.text((100, y), "Description", fill='black', font=self.font_medium)
        draw.text((1500, y), "Amount", fill='black', font=self.font_medium)
        y += 80
        
        draw.text((100, y), "Consulting Services", fill='black', font=self.font_small)
        draw.text((1500, y), "$1,200.00", fill='black', font=self.font_small)
        y += 60
        
        draw.text((100, y), "Software Development", fill='black', font=self.font_small)
        draw.text((1500, y), "$800.00", fill='black', font=self.font_small)
        y += 100
        
        # Total
        draw.line([(1400, y), (2000, y)], fill='black', width=3)
        y += 20
        draw.text((1200, y), "Total:", fill='black', font=self.font_medium)
        draw.text((1500, y), "$2,000.00", fill='black', font=self.font_medium)
        y += 100
        
        # Footer
        draw.text((100, y), "Payment Terms: Net 30", fill='black', font=self.font_small)
        y += 60
        draw.text((100, y), "Thank you for your business!", fill='black', font=self.font_small)
        
        # Save
        filepath = self.output_dir / "invoice_english.png"
        img.save(filepath)
        logger.info(f"Generated: {filepath}")
        return str(filepath)
    
    def generate_invoice_french(self) -> str:
        """Generate French invoice."""
        img = Image.new('RGB', (self.width, self.height), 'white')
        draw = ImageDraw.Draw(img)
        
        y = 100
        
        # Header
        draw.text((100, y), "FACTURE", fill='black', font=self.font_large)
        y += 120
        
        # Company info
        draw.text((100, y), "Société ACME", fill='black', font=self.font_medium)
        y += 60
        draw.text((100, y), "123 Rue des Affaires", fill='black', font=self.font_small)
        y += 50
        draw.text((100, y), "Paris, 75001 France", fill='black', font=self.font_small)
        y += 100
        
        # Invoice details
        draw.text((100, y), "Numéro de facture: FAC-2025-001", fill='black', font=self.font_small)
        y += 60
        draw.text((100, y), "Date: 8 novembre 2025", fill='black', font=self.font_small)
        y += 60
        draw.text((100, y), "Date d'échéance: 8 décembre 2025", fill='black', font=self.font_small)
        y += 100
        
        # Bill to
        draw.text((100, y), "Facturé à:", fill='black', font=self.font_medium)
        y += 60
        draw.text((100, y), "Marie Dubois", fill='black', font=self.font_small)
        y += 50
        draw.text((100, y), "456 Avenue du Client", fill='black', font=self.font_small)
        y += 50
        draw.text((100, y), "Lyon, 69001 France", fill='black', font=self.font_small)
        y += 100
        
        # Line items
        draw.text((100, y), "Description", fill='black', font=self.font_medium)
        draw.text((1500, y), "Montant", fill='black', font=self.font_medium)
        y += 80
        
        draw.text((100, y), "Services de conseil", fill='black', font=self.font_small)
        draw.text((1500, y), "€1,200.00", fill='black', font=self.font_small)
        y += 60
        
        draw.text((100, y), "Développement logiciel", fill='black', font=self.font_small)
        draw.text((1500, y), "€800.00", fill='black', font=self.font_small)
        y += 100
        
        # Total
        draw.line([(1400, y), (2000, y)], fill='black', width=3)
        y += 20
        draw.text((1200, y), "Total:", fill='black', font=self.font_medium)
        draw.text((1500, y), "€2,000.00", fill='black', font=self.font_medium)
        y += 100
        
        # Footer
        draw.text((100, y), "Conditions de paiement: 30 jours nets", fill='black', font=self.font_small)
        y += 60
        draw.text((100, y), "Merci pour votre confiance!", fill='black', font=self.font_small)
        
        # Save
        filepath = self.output_dir / "invoice_french.png"
        img.save(filepath)
        logger.info(f"Generated: {filepath}")
        return str(filepath)
    
    def generate_receipt_english(self) -> str:
        """Generate English receipt."""
        img = Image.new('RGB', (self.width, self.height), 'white')
        draw = ImageDraw.Draw(img)
        
        y = 100
        
        # Header
        draw.text((800, y), "RECEIPT", fill='black', font=self.font_large)
        y += 120
        
        # Store info
        draw.text((700, y), "Coffee & Bakery", fill='black', font=self.font_medium)
        y += 60
        draw.text((650, y), "789 Main Street, Suite 100", fill='black', font=self.font_small)
        y += 50
        draw.text((800, y), "Boston, MA 02101", fill='black', font=self.font_small)
        y += 100
        
        # Receipt details
        draw.text((100, y), "Date: November 8, 2025", fill='black', font=self.font_small)
        y += 60
        draw.text((100, y), "Time: 10:30 AM", fill='black', font=self.font_small)
        y += 60
        draw.text((100, y), "Receipt #: REC-12345", fill='black', font=self.font_small)
        y += 100
        
        # Items
        draw.text((100, y), "Item", fill='black', font=self.font_medium)
        draw.text((1500, y), "Price", fill='black', font=self.font_medium)
        y += 80
        
        draw.text((100, y), "Latte (Grande)", fill='black', font=self.font_small)
        draw.text((1500, y), "$4.50", fill='black', font=self.font_small)
        y += 60
        
        draw.text((100, y), "Croissant", fill='black', font=self.font_small)
        draw.text((1500, y), "$3.00", fill='black', font=self.font_small)
        y += 60
        
        draw.text((100, y), "Blueberry Muffin", fill='black', font=self.font_small)
        draw.text((1500, y), "$2.75", fill='black', font=self.font_small)
        y += 100
        
        # Subtotal and tax
        draw.text((1200, y), "Subtotal:", fill='black', font=self.font_small)
        draw.text((1500, y), "$10.25", fill='black', font=self.font_small)
        y += 60
        
        draw.text((1200, y), "Tax (8.25%):", fill='black', font=self.font_small)
        draw.text((1500, y), "$0.85", fill='black', font=self.font_small)
        y += 80
        
        # Total
        draw.line([(1400, y), (2000, y)], fill='black', width=3)
        y += 20
        draw.text((1200, y), "Total:", fill='black', font=self.font_medium)
        draw.text((1500, y), "$11.10", fill='black', font=self.font_medium)
        y += 100
        
        # Payment
        draw.text((100, y), "Payment Method: Credit Card ****1234", fill='black', font=self.font_small)
        y += 80
        
        draw.text((700, y), "Thank you for your visit!", fill='black', font=self.font_small)
        
        # Save
        filepath = self.output_dir / "receipt_english.png"
        img.save(filepath)
        logger.info(f"Generated: {filepath}")
        return str(filepath)
    
    def generate_contract_english(self) -> str:
        """Generate English contract snippet."""
        img = Image.new('RGB', (self.width, self.height), 'white')
        draw = ImageDraw.Draw(img)
        
        y = 100
        
        # Header
        draw.text((600, y), "SERVICE AGREEMENT", fill='black', font=self.font_large)
        y += 120
        
        # Date
        draw.text((100, y), "Effective Date: November 8, 2025", fill='black', font=self.font_small)
        y += 100
        
        # Parties
        draw.text((100, y), "This Service Agreement (the 'Agreement') is entered into by and", fill='black', font=self.font_small)
        y += 60
        draw.text((100, y), "between:", fill='black', font=self.font_small)
        y += 80
        
        draw.text((100, y), "Party A: ACME Corporation", fill='black', font=self.font_small)
        y += 50
        draw.text((200, y), "Address: 123 Business Street, New York, NY 10001", fill='black', font=self.font_small)
        y += 80
        
        draw.text((100, y), "Party B: Tech Solutions LLC", fill='black', font=self.font_small)
        y += 50
        draw.text((200, y), "Address: 456 Innovation Drive, San Francisco, CA 94101", fill='black', font=self.font_small)
        y += 100
        
        # Terms
        draw.text((100, y), "1. TERM OF AGREEMENT", fill='black', font=self.font_medium)
        y += 70
        draw.text((100, y), "This Agreement shall commence on November 8, 2025 and shall", fill='black', font=self.font_small)
        y += 60
        draw.text((100, y), "continue for a period of twelve (12) months unless terminated", fill='black', font=self.font_small)
        y += 60
        draw.text((100, y), "earlier in accordance with the terms herein.", fill='black', font=self.font_small)
        y += 100
        
        draw.text((100, y), "2. COMPENSATION", fill='black', font=self.font_medium)
        y += 70
        draw.text((100, y), "Party A agrees to pay Party B the sum of $50,000 (Fifty", fill='black', font=self.font_small)
        y += 60
        draw.text((100, y), "Thousand US Dollars) for services rendered under this", fill='black', font=self.font_small)
        y += 60
        draw.text((100, y), "Agreement, payable in monthly installments of $4,166.67.", fill='black', font=self.font_small)
        y += 100
        
        draw.text((100, y), "3. TERMINATION", fill='black', font=self.font_medium)
        y += 70
        draw.text((100, y), "Either party may terminate this Agreement with thirty (30)", fill='black', font=self.font_small)
        y += 60
        draw.text((100, y), "days written notice to the other party.", fill='black', font=self.font_small)
        y += 150
        
        # Signatures
        draw.text((100, y), "Party A Signature: _____________________", fill='black', font=self.font_small)
        draw.text((1300, y), "Date: _________", fill='black', font=self.font_small)
        y += 100
        
        draw.text((100, y), "Party B Signature: _____________________", fill='black', font=self.font_small)
        draw.text((1300, y), "Date: _________", fill='black', font=self.font_small)
        
        # Save
        filepath = self.output_dir / "contract_english.png"
        img.save(filepath)
        logger.info(f"Generated: {filepath}")
        return str(filepath)
    
    def generate_all(self) -> list[str]:
        """Generate all test documents."""
        filepaths = []
        
        logger.info("Generating test documents...")
        
        filepaths.append(self.generate_invoice_english())
        filepaths.append(self.generate_invoice_french())
        filepaths.append(self.generate_receipt_english())
        filepaths.append(self.generate_contract_english())
        
        logger.info(f"Generated {len(filepaths)} test documents in {self.output_dir}")
        return filepaths


if __name__ == '__main__':
    generator = DocumentGenerator()
    files = generator.generate_all()
    
    print("\nGenerated test documents:")
    for f in files:
        print(f"  - {f}")
