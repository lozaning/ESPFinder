#!/usr/bin/env python3
"""Quick test script to process local sample PDFs directly"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from src.config import Config
from src.database.database import db
from src.database.models import Product, PDF, Photo
from src.pdf_processor.pdf_processor import PDFProcessor
import structlog

# Setup logging
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(20),
)

logger = structlog.get_logger()

def test_local_pdf_processing():
    """Test processing local sample PDFs directly"""

    # Initialize database
    db.create_tables()
    session = db.get_session()

    try:
        # Create sample products and PDFs with local file paths
        sample_data = [
            {'fcc_id': 'SAMPLE001', 'applicant': 'Apple Inc.', 'product_name': 'iPhone Test Device'},
            {'fcc_id': 'SAMPLE002', 'applicant': 'Google LLC', 'product_name': 'Pixel Test Device'},
            {'fcc_id': 'SAMPLE003', 'applicant': 'Samsung Electronics', 'product_name': 'Galaxy Test Device'},
        ]

        for sample in sample_data:
            # Check if product already exists
            product = session.query(Product).filter_by(fcc_id=sample['fcc_id']).first()

            if not product:
                product = Product(
                    fcc_id=sample['fcc_id'],
                    applicant=sample['applicant'],
                    product_name=sample['product_name']
                )
                session.add(product)
                session.flush()

                # Add PDF with local file path
                internal_photos_path = os.path.join('data', 'sample_pdfs', f"{sample['fcc_id']}_Internal_Photos.pdf")

                if os.path.exists(internal_photos_path):
                    pdf = PDF(
                        product_id=product.id,
                        filename=f"{sample['fcc_id']}_Internal_Photos.pdf",
                        url=f"file://{os.path.abspath(internal_photos_path)}",
                        local_path=os.path.abspath(internal_photos_path),
                        downloaded=True  # Already downloaded (local file)
                    )
                    session.add(pdf)
                    logger.info(f"Added PDF for {sample['fcc_id']}")

        session.commit()
        logger.info("Database populated with sample data")

        # Process PDFs
        processor = PDFProcessor()
        session.close()
        session = db.get_session()

        unprocessed_pdfs = session.query(PDF).filter_by(processed=False).all()
        logger.info(f"Found {len(unprocessed_pdfs)} unprocessed PDFs")

        total_images = 0
        for pdf in unprocessed_pdfs:
            logger.info(f"Processing {pdf.filename}...")
            photos = processor.extract_images_from_pdf(pdf)
            total_images += len(photos)
            logger.info(f"  Extracted {len(photos)} images")

        # Show results
        session.close()
        session = db.get_session()

        total_products = session.query(Product).count()
        total_photos = session.query(Photo).count()

        logger.info(f"\n=== RESULTS ===")
        logger.info(f"Products: {total_products}")
        logger.info(f"Photos extracted: {total_photos}")
        logger.info(f"Images saved to: {Config.IMAGES_DIR}")

        # List images by product
        products = session.query(Product).all()
        for product in products:
            photo_count = len(product.photos)
            if photo_count > 0:
                logger.info(f"\n{product.fcc_id}: {photo_count} photos")
                image_dir = os.path.join(Config.IMAGES_DIR, product.fcc_id)
                if os.path.exists(image_dir):
                    files = os.listdir(image_dir)
                    for f in files[:5]:  # Show first 5
                        logger.info(f"  - {f}")
                    if len(files) > 5:
                        logger.info(f"  ... and {len(files)-5} more")

        return total_photos > 0

    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
        return False
    finally:
        session.close()

if __name__ == '__main__':
    success = test_local_pdf_processing()
    sys.exit(0 if success else 1)
