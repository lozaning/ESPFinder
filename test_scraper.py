#!/usr/bin/env python3

import sys
sys.path.append('/home/lozaning/ESPFinder')

from src.scraper.fcc_scraper import FCCScraper
import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)

def test_scraper():
    print("=== Testing FCC Scraper ===")
    
    scraper = FCCScraper()
    
    print("\n1. Testing search_recent_filings...")
    filings = scraper.search_recent_filings(days_back=7)
    
    print(f"Found {len(filings)} filings")
    
    if filings:
        print("\nSample filings:")
        for i, filing in enumerate(filings[:3]):
            print(f"  {i+1}. FCC ID: {filing['fcc_id']}")
            print(f"     Applicant: {filing['applicant']}")
            print(f"     Product: {filing['product_name']}")
            print(f"     Detail URL: {filing['detail_url']}")
            print()
    
    print("\n2. Testing get_filing_details...")
    if filings:
        test_fcc_id = filings[0]['fcc_id']
        print(f"Getting details for {test_fcc_id}...")
        
        details = scraper.get_filing_details(test_fcc_id)
        if details:
            print(f"Found {len(details.get('pdfs', []))} PDFs")
            for pdf in details.get('pdfs', []):
                print(f"  - {pdf['filename']}")
        else:
            print("No details found")
    
    return len(filings) > 0

if __name__ == "__main__":
    success = test_scraper()
    if success:
        print("\n✅ Scraper test PASSED - ready for deployment")
        sys.exit(0)
    else:
        print("\n❌ Scraper test FAILED - needs fixing")
        sys.exit(1)