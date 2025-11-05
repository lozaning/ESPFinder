#!/usr/bin/env python3
"""
Real PDF Extraction Test for ESPFinder

This test uses a real internal photos PDF from an actual FCC filing
to test the complete image extraction pipeline:

1. Download real PDF with internal photos from FCC filing
2. Extract images from the PDF
3. Save images to disk
4. Verify the entire pipeline works with real data

Uses PDF from: FCC ID 2AAE9CAUVST05 (Smart UV Lamp)
PDF URL: https://fcc.report/FCC-ID/2AAE9CAUVST05/4998795.pdf
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import structlog

# Add project root to path
sys.path.insert(0, '/home/user/ESPFinder')

from src.config import Config
from src.database.database import db
from src.database.models import Product, PDF, Photo
from src.pdf_processor.pdf_processor import PDFProcessor

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()


def test_real_pdf_extraction():
    """Test PDF extraction with real FCC internal photos PDF"""

    print("\n" + "="*80)
    print("ESPFinder Real PDF Extraction Test")
    print("="*80)
    print(f"\nTest started at: {datetime.now().isoformat()}")

    # Setup
    Config.ensure_dirs()
    db.create_tables()

    print("\n" + "-"*80)
    print("Test Details")
    print("-"*80)
    print("FCC ID: 2AAE9CAUVST05")
    print("Product: Smart UV Lamp")
    print("Manufacturer: GNJ Manufacturing Inc.")
    print("PDF: Internal Photos (real FCC filing)")
    print("Source: fcc.report (official FCC data mirror)")
    print("-"*80)

    # Real FCC filing data
    fcc_id = "2AAE9CAUVST05"
    product_name = "Smart UV Lamp"
    applicant = "GNJ Manufacturing Inc."

    # Real internal photos PDF from actual FCC filing
    real_pdf_url = "https://fcc.report/FCC-ID/2AAE9CAUVST05/4998795.pdf"
    pdf_filename = "Internal_Photos.pdf"

    print("\n[1/5] Creating database records...")

    session = db.get_session()
    try:
        # Check if product already exists
        product = session.query(Product).filter_by(fcc_id=fcc_id).first()

        if not product:
            product = Product(
                fcc_id=fcc_id,
                applicant=applicant,
                product_name=product_name,
                filing_date=datetime.now()
            )
            session.add(product)
            session.flush()
            print(f"[OK] Created product record (ID: {product.id})")
        else:
            print(f"[OK] Using existing product record (ID: {product.id})")

        # Check if PDF already exists
        pdf = session.query(PDF).filter_by(
            product_id=product.id,
            url=real_pdf_url
        ).first()

        if not pdf:
            pdf = PDF(
                product_id=product.id,
                filename=pdf_filename,
                url=real_pdf_url
            )
            session.add(pdf)
            session.flush()
            print(f"[OK] Created PDF record (ID: {pdf.id})")
        else:
            print(f"[OK] Using existing PDF record (ID: {pdf.id})")

        session.commit()
        pdf_id = pdf.id

    except Exception as e:
        session.rollback()
        print(f"[FAIL] Error creating database records: {e}")
        return False
    finally:
        session.close()

    print("\n[2/5] Downloading real PDF from FCC filing...")
    print(f"URL: {real_pdf_url}")

    processor = PDFProcessor()

    session = db.get_session()
    try:
        pdf = session.query(PDF).filter_by(id=pdf_id).first()

        # Force re-download if needed
        if pdf.downloaded and pdf.local_path and os.path.exists(pdf.local_path):
            print(f"[INFO] PDF already downloaded: {pdf.local_path}")
            print(f"  Size: {os.path.getsize(pdf.local_path)} bytes")
        else:
            if processor.download_pdf(pdf):
                # Close and reopen session to get updated data
                session.close()
                session = db.get_session()
                pdf = session.query(PDF).filter_by(id=pdf_id).first()

                print(f"[OK] Downloaded PDF successfully!")
                print(f"  Local path: {pdf.local_path}")
                print(f"  Size: {pdf.file_size} bytes")
            else:
                print(f"[FAIL] Failed to download PDF")
                return False

    finally:
        session.close()

    print("\n[3/5] Extracting images from PDF...")

    session = db.get_session()
    try:
        pdf = session.query(PDF).filter_by(id=pdf_id).first()

        if not pdf.local_path or not os.path.exists(pdf.local_path):
            print(f"[FAIL] PDF file not found: {pdf.local_path}")
            return False

        # Delete existing photos for fresh extraction
        existing_photos = session.query(Photo).filter_by(pdf_id=pdf_id).all()
        if existing_photos:
            print(f"[INFO] Removing {len(existing_photos)} existing photos for fresh extraction")
            for photo in existing_photos:
                if os.path.exists(photo.local_path):
                    os.remove(photo.local_path)
                session.delete(photo)
            session.commit()

        # Mark as unprocessed to force reprocessing
        pdf.processed = False
        session.commit()

        print(f"  Processing: {pdf.local_path}")

        # Count images in PDF first
        import fitz
        doc = fitz.open(pdf.local_path)
        total_pdf_images = sum(len(doc.load_page(i).get_images()) for i in range(len(doc)))
        doc.close()
        print(f"  PDF contains {total_pdf_images} extractable images")

        photos = processor.extract_images_from_pdf(pdf)
        photo_count = len(photos)

        if photo_count > 0:
            print(f"[OK] Extracted {photo_count} images from PDF")
        else:
            print(f"[INFO] No images extracted from PDF")
            print("  Note: PDF may not contain extractable images,")
            print("        or images may not meet size/quality requirements")

    finally:
        session.close()

    print("\n[4/5] Verifying extracted images...")

    session = db.get_session()
    try:
        product = session.query(Product).filter_by(fcc_id=fcc_id).first()
        photos = session.query(Photo).filter_by(product_id=product.id).all()

        print(f"\n[SUMMARY] Extraction Results:")
        print(f"  Product: {product.product_name} ({product.fcc_id})")
        print(f"  Photos in database: {len(photos)}")

        if photos:
            print(f"\n  Extracted Images:")

            valid_photos = []
            for i, photo in enumerate(photos, 1):
                exists = os.path.exists(photo.local_path)
                status = "[OK]" if exists else "[FAIL]"

                if exists:
                    valid_photos.append(photo)
                    file_size_kb = photo.file_size / 1024 if photo.file_size else 0

                    print(f"\n    {i}. {photo.filename}")
                    print(f"       Status: {status} File exists")
                    print(f"       Size: {photo.width}x{photo.height} pixels, {file_size_kb:.1f} KB")
                    print(f"       Location: {photo.local_path}")
                    if photo.page_number:
                        print(f"       Source: Page {photo.page_number} of PDF")
                else:
                    print(f"\n    {i}. {photo.filename}")
                    print(f"       Status: {status} FILE MISSING")
                    print(f"       Expected location: {photo.local_path}")

            print(f"\n  Valid photos: {len(valid_photos)}/{len(photos)}")

            return len(valid_photos) > 0
        else:
            print("\n  [WARN]  No photos extracted")
            return False

    finally:
        session.close()


def main():
    """Main test entry point"""

    try:
        print("\n" + "="*80)
        print("Testing ESPFinder with Real FCC Data")
        print("="*80)
        print("\nThis test uses a real internal photos PDF from an actual FCC filing")
        print("to verify ESPFinder can download and extract photos from real data.")
        print("\nFCC Filing: 2AAE9CAUVST05 (Smart UV Lamp by GNJ Manufacturing Inc.)")

        success = test_real_pdf_extraction()

        print("\n" + "="*80)
        if success:
            print(" TEST PASSED: ESPFinder Successfully Processed Real FCC Data!")
            print("="*80)
            print("\nESPFinder successfully:")
            print("  [OK] Downloaded real internal photos PDF from FCC filing")
            print("  [OK] Extracted actual product images from the PDF")
            print("  [OK] Saved images to local storage")
            print("  [OK] Stored metadata in database")
            print("\n[PASS] ESPFinder is working correctly with real-world FCC data!")
        else:
            print("[WARN]  TEST INCOMPLETE: Could not extract images from PDF")
            print("="*80)
            print("\nPossible reasons:")
            print("  - PDF format may not contain extractable raster images")
            print("  - Images may be embedded as vector graphics")
            print("  - Images may not meet minimum size requirements")
            print("\nNote: ESPFinder successfully downloaded the PDF,")
            print("      image extraction depends on PDF content format")

        print(f"\nTest completed at: {datetime.now().isoformat()}")
        print("="*80)

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
