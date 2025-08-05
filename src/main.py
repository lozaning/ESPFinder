#!/usr/bin/env python3

import structlog
import sys
from datetime import datetime

from .config import Config
from .database.database import db
from .scraper.fcc_scraper import FCCScraper
from .pdf_processor.pdf_processor import PDFProcessor

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

def main():
    logger.info("Starting ESPFinder")
    
    Config.ensure_dirs()
    
    db.create_tables()
    logger.info("Database initialized")
    
    scraper = FCCScraper()
    processor = PDFProcessor()
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            logger.info(f"Searching for recent FCC filings (attempt {retry_count + 1}/{max_retries})...")
            filings = scraper.search_recent_filings(days_back=7)
            
            if not filings:
                logger.warning("No filings found. FCC website may be unavailable.")
                if retry_count < max_retries - 1:
                    import time
                    wait_time = (retry_count + 1) * 60  # Wait 1, 2, 3 minutes
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    retry_count += 1
                    continue
                else:
                    logger.error("Max retries reached. Exiting.")
                    break
            
            logger.info(f"Found {len(filings)} filings to process")
            
            for filing in filings:
                logger.info(f"Processing filing: {filing['fcc_id']}")
                
                details = scraper.get_filing_details(filing['fcc_id'])
                if details and details.get('pdfs'):
                    filing.update(details)
                    product = scraper.save_to_database(filing)
                    
                    if product:
                        logger.info(f"Saved product {product.fcc_id}, processing PDFs...")
                        
            logger.info("Processing unprocessed PDFs...")
            processed_count = processor.process_unprocessed_pdfs()
            logger.info(f"Processed {processed_count} PDFs")
            
            logger.info("ESPFinder completed successfully")
            break  # Success, exit retry loop
            
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            retry_count += 1
            if retry_count < max_retries:
                import time
                wait_time = retry_count * 30  # Wait 30, 60 seconds
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error("Max retries reached. Exiting gracefully.")
                sys.exit(1)

if __name__ == "__main__":
    main()