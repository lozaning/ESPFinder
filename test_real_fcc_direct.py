#!/usr/bin/env python3
"""
Direct End-to-End Test for ESPFinder with Real FCC Data

This test directly accesses the FCC website to:
1. Get real FCC filing details
2. Download actual internal photos PDFs
3. Extract images from them
4. Verify the complete pipeline works

No Selenium required - uses direct HTTP requests.
"""

import sys
import os
import requests
from bs4 import BeautifulSoup
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


class DirectFCCTest:
    """Direct FCC test without Selenium"""

    def __init__(self):
        self.processor = PDFProcessor()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def setup(self):
        """Setup test environment"""
        print("\n" + "="*80)
        print("ESPFinder Real FCC Data Test (Direct HTTP)")
        print("="*80)
        print(f"\nTest started at: {datetime.now().isoformat()}")

        # Ensure directories exist
        Config.ensure_dirs()

        # Initialize database
        db.create_tables()
        logger.info("Test environment initialized")

    def get_real_fcc_filing(self, fcc_id: str):
        """
        Get real FCC filing details and PDF URLs directly from FCC website

        Args:
            fcc_id: FCC ID to look up (e.g., "2AAE9CAUVST05")

        Returns:
            dict with filing details and PDF URLs, or None if not found
        """
        print(f"\n{'='*80}")
        print(f"Testing with Real FCC ID: {fcc_id}")
        print(f"{'='*80}")

        # Build FCC exhibit URL
        exhibit_url = f"https://apps.fcc.gov/oetcf/eas/reports/ViewExhibitReport.cfm?mode=Exhibits&RequestTimeout=500&calledFromFrame=N&application_id={fcc_id}"

        print(f"\n[1/5] Fetching FCC filing page...")
        print(f"URL: {exhibit_url}")

        try:
            response = self.session.get(exhibit_url, timeout=30)
            response.raise_for_status()

            print(f"✓ Successfully retrieved FCC page ({len(response.content)} bytes)")

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find all PDF links
            pdf_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                text = link.get_text(strip=True).lower()

                if '.pdf' in href.lower():
                    # Check if it's an internal photos PDF
                    if any(keyword in text for keyword in ['internal', 'int', 'photo', 'inside', 'pcb']):
                        full_url = self._build_full_url(href)
                        pdf_links.append({
                            'filename': link.get_text(strip=True),
                            'url': full_url,
                            'fcc_id': fcc_id
                        })
                        print(f"  Found internal photos PDF: {link.get_text(strip=True)}")

            if pdf_links:
                print(f"\n✓ Found {len(pdf_links)} internal photos PDF(s)")
                return {
                    'fcc_id': fcc_id,
                    'pdfs': pdf_links
                }
            else:
                print(f"\n○ No internal photos PDFs found for {fcc_id}")
                print("  (This FCC ID may not have internal photos available)")
                return None

        except requests.RequestException as e:
            print(f"\n✗ Error fetching FCC page: {e}")
            return None

    def _build_full_url(self, href: str) -> str:
        """Build full URL from relative href"""
        if href.startswith('http'):
            return href
        elif href.startswith('/'):
            return 'https://apps.fcc.gov' + href
        else:
            return f"https://apps.fcc.gov/oetcf/eas/reports/{href}"

    def test_fcc_id(self, fcc_id: str, product_name: str, applicant: str):
        """Test complete pipeline with a single FCC ID"""

        # Step 1: Get filing details
        details = self.get_real_fcc_filing(fcc_id)

        if not details or not details.get('pdfs'):
            print(f"\n⚠️  Cannot test {fcc_id} - no internal photos PDFs found")
            return False

        # Step 2: Save to database
        print(f"\n[2/5] Saving product to database...")

        session = db.get_session()
        try:
            product = Product(
                fcc_id=fcc_id,
                applicant=applicant,
                product_name=product_name,
                filing_date=datetime.now()
            )
            session.add(product)
            session.flush()

            for pdf_data in details['pdfs']:
                pdf = PDF(
                    product_id=product.id,
                    filename=pdf_data['filename'],
                    url=pdf_data['url']
                )
                session.add(pdf)

            session.commit()
            product_id = product.id
            print(f"✓ Saved product with ID: {product_id}")

        except Exception as e:
            session.rollback()
            print(f"✗ Error saving to database: {e}")
            return False
        finally:
            session.close()

        # Step 3: Download PDFs
        print(f"\n[3/5] Downloading PDFs from FCC servers...")

        session = db.get_session()
        try:
            pdfs = session.query(PDF).filter_by(product_id=product_id).all()
            downloaded_count = 0

            for pdf in pdfs:
                print(f"  Downloading: {pdf.filename}...")
                print(f"  URL: {pdf.url}")

                if self.processor.download_pdf(pdf):
                    print(f"  ✓ Downloaded successfully ({pdf.file_size} bytes)")
                    downloaded_count += 1
                else:
                    print(f"  ✗ Download failed")

            if downloaded_count == 0:
                print(f"\n✗ No PDFs were downloaded successfully")
                return False

            print(f"\n✓ Downloaded {downloaded_count}/{len(pdfs)} PDF(s)")

        finally:
            session.close()

        # Step 4: Extract images
        print(f"\n[4/5] Extracting images from PDFs...")

        session = db.get_session()
        try:
            pdfs = session.query(PDF).filter_by(product_id=product_id, downloaded=True).all()
            total_images = 0

            for pdf in pdfs:
                print(f"  Processing: {pdf.filename}...")
                photos = self.processor.extract_images_from_pdf(pdf)
                image_count = len(photos)

                if image_count > 0:
                    print(f"  ✓ Extracted {image_count} image(s)")
                    total_images += image_count
                else:
                    print(f"  ○ No images extracted")

            print(f"\n✓ Total images extracted: {total_images}")

        finally:
            session.close()

        # Step 5: Verify results
        print(f"\n[5/5] Verifying results...")

        session = db.get_session()
        try:
            product = session.query(Product).filter_by(fcc_id=fcc_id).first()
            photos = session.query(Photo).filter_by(product_id=product.id).all()

            print(f"\n📊 Final Summary:")
            print(f"  Product: {product.product_name} ({product.fcc_id})")
            print(f"  PDFs downloaded: {downloaded_count}")
            print(f"  Photos extracted: {len(photos)}")

            if photos:
                print(f"\n  Extracted photos:")
                for i, photo in enumerate(photos[:5], 1):  # Show first 5
                    exists = os.path.exists(photo.local_path)
                    status = "✓" if exists else "✗"
                    size = f"{photo.file_size} bytes" if photo.file_size else "unknown size"
                    print(f"    {status} {photo.filename} - {photo.width}x{photo.height} pixels, {size}")
                    print(f"       Location: {photo.local_path}")

                if len(photos) > 5:
                    print(f"    ... and {len(photos) - 5} more photos")

                # Verify at least one image file exists
                existing_photos = [p for p in photos if os.path.exists(p.local_path)]
                if existing_photos:
                    print(f"\n✅ TEST PASSED: Successfully downloaded and extracted {len(existing_photos)} real photos from FCC!")
                    return True
                else:
                    print(f"\n⚠️  Photos extracted but files not found on disk")
                    return False
            else:
                print(f"\n⚠️  No photos were extracted (PDF may not contain extractable images)")
                return False

        finally:
            session.close()

    def run(self):
        """Run the test"""
        self.setup()

        # Test with a real FCC ID that we know has internal photos
        # We'll try multiple FCC IDs until we find one with photos
        test_cases = [
            ('2AAE9CAUVST05', 'Smart UV Lamp', 'GNJ Manufacturing Inc.'),
            ('2AJGP-WLAN01', 'Wireless Device', 'Unknown'),
            ('2ANMU-WP12', 'Wireless Product', 'Unknown'),
        ]

        success = False
        for fcc_id, product_name, applicant in test_cases:
            result = self.test_fcc_id(fcc_id, product_name, applicant)
            if result:
                success = True
                break
            else:
                print(f"\n  Trying next FCC ID...")

        print(f"\n{'='*80}")
        if success:
            print("🎉 END-TO-END TEST SUCCESSFUL!")
            print("\nESPFinder successfully:")
            print("  ✓ Connected to real FCC website")
            print("  ✓ Retrieved real filing information")
            print("  ✓ Downloaded real PDFs from FCC servers")
            print("  ✓ Extracted actual internal photos")
            print("  ✓ Saved everything to database and filesystem")
            print("\n✅ ESPFinder is working end-to-end with real FCC data!")
        else:
            print("⚠️  Test completed but couldn't find FCC IDs with downloadable photos")
            print("   (This may be due to FCC website restrictions or data availability)")

        print(f"\nTest completed at: {datetime.now().isoformat()}")
        print("="*80)

        return success


def main():
    """Main test entry point"""
    try:
        tester = DirectFCCTest()
        success = tester.run()
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
