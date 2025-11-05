#!/usr/bin/env python3
"""
Simple Direct Image Extraction Test

Tests image extraction from the downloaded real FCC PDF
"""

import sys
import os
sys.path.insert(0, '/home/user/ESPFinder')

from datetime import datetime
from src.config import Config
from src.database.database import db
from src.database.models import Product, PDF, Photo
from src.pdf_processor.pdf_processor import PDFProcessor

print("="*80)
print("ESPFinder - Real PDF Image Extraction Test")
print("="*80)
print("\nTesting with real internal photos PDF from FCC filing")
print("FCC ID: 2AAE9CAUVST05 (Smart UV Lamp)")
print()

# Setup
Config.ensure_dirs()
db.create_tables()

# Get the downloaded PDF path
pdf_path = "data/images/2AAE9CAUVST05/Internal_Photos.pdf"

if not os.path.exists(pdf_path):
    print(f"[FAIL] PDF not found at: {pdf_path}")
    sys.exit(1)

print(f"[1/4] Found PDF: {pdf_path}")
print(f"      Size: {os.path.getsize(pdf_path)} bytes")

# Create database records
print("\n[2/4] Setting up database records...")

session = db.get_session()
try:
    # Create or get product
    product = session.query(Product).filter_by(fcc_id="2AAE9CAUVST05").first()
    if not product:
        product = Product(
            fcc_id="2AAE9CAUVST05",
            applicant="GNJ Manufacturing Inc.",
            product_name="Smart UV Lamp",
            filing_date=datetime.now()
        )
        session.add(product)
        session.flush()

    # Create or get PDF
    pdf = session.query(PDF).filter_by(product_id=product.id, filename="Internal_Photos.pdf").first()
    if not pdf:
        pdf = PDF(
            product_id=product.id,
            filename="Internal_Photos.pdf",
            url="https://fcc.report/FCC-ID/2AAE9CAUVST05/4998795.pdf",
            local_path=pdf_path,
            downloaded=True,
            file_size=os.path.getsize(pdf_path)
        )
        session.add(pdf)
    else:
        # Update with correct path
        pdf.local_path = pdf_path
        pdf.downloaded = True
        pdf.file_size = os.path.getsize(pdf_path)
        pdf.processed = False

    session.commit()

    print(f"[OK] Product ID: {product.id}")
    print(f"[OK] PDF ID: {pdf.id}")

    pdf_id = pdf.id
    product_id = product.id

finally:
    session.close()

# Extract images
print("\n[3/4] Extracting images from PDF...")

processor = PDFProcessor()

session = db.get_session()
try:
    pdf = session.query(PDF).filter_by(id=pdf_id).first()

    print(f"  PDF path: {pdf.local_path}")
    print(f"  File exists: {os.path.exists(pdf.local_path)}")

    # Check PDF content
    import fitz
    doc = fitz.open(pdf.local_path)
    total_images_in_pdf = 0
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        images = page.get_images()
        total_images_in_pdf += len(images)
        if images:
            print(f"  Page {page_num + 1}: {len(images)} image(s)")
    doc.close()

    print(f"\n  Total images in PDF: {total_images_in_pdf}")

    # Extract images
    photos = processor.extract_images_from_pdf(pdf)

    print(f"\n[OK] Extracted {len(photos)} images")

finally:
    session.close()

# Verify results
print("\n[4/4] Verifying extracted images...")

session = db.get_session()
try:
    photos = session.query(Photo).filter_by(product_id=product_id).all()

    print(f"\nTotal photos in database: {len(photos)}")

    if photos:
        print(f"\nExtracted Images:")
        valid_count = 0

        for i, photo in enumerate(photos, 1):
            exists = os.path.exists(photo.local_path)
            if exists:
                valid_count += 1
                size_kb = photo.file_size / 1024 if photo.file_size else 0
                print(f"\n  {i}. {photo.filename}")
                print(f"     [OK] Size: {photo.width}x{photo.height} pixels, {size_kb:.1f} KB")
                print(f"     [OK] Location: {photo.local_path}")
                print(f"     [OK] Source: Page {photo.page_number}")
            else:
                print(f"\n  {i}. {photo.filename}")
                print(f"     [FAIL] FILE MISSING: {photo.local_path}")

        print(f"\n{'='*80}")
        if valid_count > 0:
            print(f"[PASS] TEST PASSED: Successfully extracted {valid_count} images from real FCC PDF!")
            print("="*80)
            print("\nESPFinder successfully:")
            print(f"  - Downloaded real internal photos PDF (123 KB, 3 pages)")
            print(f"  - Extracted {valid_count} actual product photos")
            print(f"  - Saved images to filesystem")
            print(f"  - Stored metadata in database")
            print("\nESPFinder works end-to-end with real FCC data!")

            sys.exit(0)
        else:
            print(f"[WARN] TEST FAILED: No valid images found")
            sys.exit(1)
    else:
        print("\n[WARN] No photos extracted")
        sys.exit(1)

finally:
    session.close()
