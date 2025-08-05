#!/usr/bin/env python3

import sys
import os
sys.path.append('/home/lozaning/ESPFinder')

from src.scraper.selenium_scraper import SeleniumFCCScraper
import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)

def test_selenium_scraper():
    print("=== Testing Selenium FCC Scraper ===")
    
    try:
        scraper = SeleniumFCCScraper()
        
        print("\n1. Testing search_recent_filings...")
        filings = scraper.search_recent_filings(days_back=1)
        
        print(f"Found {len(filings)} filings")
        
        if filings:
            print("\nSample filings:")
            for i, filing in enumerate(filings[:3]):
                print(f"  {i+1}. FCC ID: {filing['fcc_id']}")
                print(f"     Applicant: {filing['applicant']}")
                print(f"     Product: {filing['product_name']}")
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
        
        scraper.close()
        return len(filings) > 0
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = test_selenium_scraper()
    if success:
        print("\n✅ Selenium scraper test PASSED - real FCC data found!")
        sys.exit(0)
    else:
        print("\n❌ Selenium scraper test FAILED")
        sys.exit(1)