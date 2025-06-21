#!/usr/bin/env python3
"""
Script to create test PDF documents for verification testing
"""

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

def create_pdf_from_text(text_file, pdf_file, title="Document"):
    """Convert text file to PDF"""
    
    # Read the text file
    with open(text_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create PDF
    doc = SimpleDocTemplate(pdf_file, pagesize=A4)
    story = []
    
    # Split content into lines
    lines = content.split('\n')
    
    # Create the PDF content
    c = canvas.Canvas(pdf_file, pagesize=A4)
    width, height = A4
    
    # Set font (try to handle Turkish characters)
    try:
        c.setFont("Helvetica", 10)
    except:
        c.setFont("Helvetica", 10)
    
    y_position = height - 50
    line_height = 12
    
    for line in lines:
        if y_position < 50:  # Start new page if needed
            c.showPage()
            y_position = height - 50
            c.setFont("Helvetica", 10)
        
        # Handle special characters by encoding properly
        try:
            # Clean line and handle Turkish characters
            clean_line = line.replace('⚠️', '[!]')  # Replace emoji with text
            c.drawString(50, y_position, clean_line)
        except:
            # Fallback for problematic characters
            clean_line = line.encode('ascii', 'ignore').decode('ascii')
            c.drawString(50, y_position, clean_line)
        
        y_position -= line_height
    
    c.save()
    print(f"✅ Created PDF: {pdf_file}")

def create_test_documents():
    """Create both test PDF documents"""
    
    # Ensure test_documents directory exists
    os.makedirs('test_documents', exist_ok=True)
    
    # Create suspicious invoice PDF
    print("🔴 Creating suspicious invoice PDF...")
    create_pdf_from_text(
        'test_documents/suspicious_invoice.txt', 
        'test_documents/suspicious_invoice.pdf',
        'Suspicious Invoice'
    )
    
    # Create clean receipt PDF  
    print("🟢 Creating clean receipt PDF...")
    create_pdf_from_text(
        'test_documents/clean_receipt.txt',
        'test_documents/clean_receipt.pdf', 
        'Clean Receipt'
    )
    
    print("\n📋 Test documents created:")
    print("- suspicious_invoice.pdf (should trigger warnings)")
    print("- clean_receipt.pdf (should pass verification)")
    print("\nYou can now test these with the document verification system!")

if __name__ == "__main__":
    create_test_documents() 