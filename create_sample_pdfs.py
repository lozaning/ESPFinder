#!/usr/bin/env python3

import os
from PIL import Image, ImageDraw, ImageFont
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def create_sample_pdf_with_images(filename, title):
    """Create a sample PDF with mock PCB images"""
    
    # Create sample images
    images = []
    
    for i in range(3):  # 3 sample images per PDF
        # Create a mock PCB image
        img = Image.new('RGB', (800, 600), color='darkgreen')
        draw = ImageDraw.Draw(img)
        
        # Draw some mock PCB components
        # Draw traces (lines)
        for j in range(10):
            x1, y1 = j * 80, j * 60
            x2, y2 = x1 + 100, y1 + 50
            draw.line([(x1, y1), (x2, y2)], fill='silver', width=3)
        
        # Draw components (rectangles)
        for j in range(5):
            x, y = j * 150 + 50, j * 100 + 100
            draw.rectangle([x, y, x + 60, y + 40], fill='black', outline='white')
            draw.text((x + 5, y + 5), f'U{j+1}', fill='white')
        
        # Draw some circular components
        for j in range(8):
            x, y = j * 90 + 30, 400 + (j % 2) * 100
            draw.ellipse([x, y, x + 20, y + 20], fill='yellow', outline='black')
        
        # Add title
        draw.text((10, 10), f"{title} - Internal Photo {i+1}", fill='white')
        
        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        images.append(img_bytes.getvalue())
    
    # Create PDF with images
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    for i, img_data in enumerate(images):
        if i > 0:
            c.showPage()  # New page for each image
        
        # Add title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, f"{title} - Page {i+1}")
        
        # Add image
        img_path = f"/tmp/temp_img_{i}.png"
        with open(img_path, 'wb') as f:
            f.write(img_data)
        
        c.drawImage(img_path, 50, height - 500, width=500, height=400)
        
        # Add some text
        c.setFont("Helvetica", 12)
        c.drawString(50, height - 520, "Internal PCB Photos")
        c.drawString(50, height - 540, "Contains sensitive component layout information")
        
        # Clean up temp file
        os.remove(img_path)
    
    c.save()
    print(f"Created {filename}")

def create_all_sample_pdfs():
    """Create sample PDFs for all sample FCC IDs"""
    
    # Create data directory
    os.makedirs("data/sample_pdfs", exist_ok=True)
    
    sample_data = [
        ("SAMPLE001", "Apple iPhone Test Device"),
        ("SAMPLE002", "Google Pixel Test Device"), 
        ("SAMPLE003", "Samsung Galaxy Test Device")
    ]
    
    for fcc_id, product_name in sample_data:
        # Create internal photos PDF
        internal_pdf = f"data/sample_pdfs/{fcc_id}_Internal_Photos.pdf"
        create_sample_pdf_with_images(internal_pdf, f"{product_name} Internal Photos")
        
        # Create test report PDF (text only)
        test_pdf = f"data/sample_pdfs/{fcc_id}_Test_Report.pdf"
        c = canvas.Canvas(test_pdf, pagesize=letter)
        width, height = letter
        
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, f"{product_name} Test Report")
        
        c.setFont("Helvetica", 12)
        y = height - 100
        test_content = [
            "FCC Test Report",
            f"FCC ID: {fcc_id}",
            f"Product: {product_name}",
            "",
            "Test Results:",
            "- Radiated Emissions: PASS",
            "- Conducted Emissions: PASS", 
            "- Spurious Emissions: PASS",
            "",
            "This device complies with FCC regulations.",
        ]
        
        for line in test_content:
            c.drawString(50, y, line)
            y -= 20
        
        c.save()
        print(f"Created {test_pdf}")

if __name__ == "__main__":
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        create_all_sample_pdfs()
        print("\n✅ Sample PDFs created successfully!")
    except ImportError:
        print("❌ Missing dependencies. Install with: pip3 install reportlab")
        print("   Run: pip3 install reportlab pillow")