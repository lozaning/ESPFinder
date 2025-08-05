import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import structlog
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup

logger = structlog.get_logger()

class SeleniumFCCScraper:
    def __init__(self):
        self.driver = None
        self._setup_driver()
    
    def _setup_driver(self):
        """Setup headless Chrome driver"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            logger.info("Selenium Chrome driver initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            raise
    
    def search_recent_filings(self, days_back: int = 1) -> List[Dict]:
        """Search FCC database using the GenericSearch form"""
        if not self.driver:
            logger.error("Chrome driver not initialized")
            return []
        
        try:
            # Calculate date range (yesterday)
            end_date = datetime.now() - timedelta(days=1)
            start_date = end_date  # Same day
            
            date_str = end_date.strftime('%m/%d/%Y')
            
            logger.info(f"Searching FCC filings for date: {date_str}")
            
            # Navigate to FCC search page
            url = "https://apps.fcc.gov/oetcf/eas/reports/GenericSearch.cfm"
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "form"))
            )
            
            # Fill in the Final Action Date Range fields
            try:
                # Find the start date field (correct field name from FCC form)
                start_date_field = self.driver.find_element(By.NAME, "grant_date_from")
                start_date_field.clear()
                start_date_field.send_keys(date_str)
                
                # Find the end date field (correct field name from FCC form)
                end_date_field = self.driver.find_element(By.NAME, "grant_date_to")
                end_date_field.clear()
                end_date_field.send_keys(date_str)
                
                logger.info(f"Filled date fields with {date_str}")
                
                # Submit the form
                submit_button = self.driver.find_element(By.NAME, "Submit")
                submit_button.click()
                
                # Wait for results to load
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "table"))
                )
                
                # Parse the results
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                
                filings = self._parse_search_results(soup)
                logger.info(f"Found {len(filings)} filings for {date_str}")
                
                return filings
                
            except NoSuchElementException as e:
                logger.error(f"Could not find form elements: {e}")
                # Save page source for debugging
                with open('/tmp/fcc_page_debug.html', 'w') as f:
                    f.write(self.driver.page_source)
                logger.info("Saved page source to /tmp/fcc_page_debug.html for debugging")
                return []
                
        except TimeoutException:
            logger.error("Timeout waiting for FCC page to load")
            return []
        except Exception as e:
            logger.error(f"Error searching FCC filings: {e}")
            return []
    
    def _parse_search_results(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse FCC search results from HTML"""
        filings = []
        
        # Look for results table
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            
            # Skip tables that are too small to contain results
            if len(rows) < 2:
                continue
                
            # Check if this looks like a results table
            header_row = rows[0]
            header_text = header_row.get_text().lower()
            
            if 'fcc' in header_text or 'id' in header_text or 'applicant' in header_text:
                logger.info(f"Found results table with {len(rows)} rows")
                
                # Parse data rows
                for row in rows[1:]:  # Skip header
                    cells = row.find_all(['td', 'th'])
                    
                    if len(cells) >= 3:
                        # Extract data from cells
                        fcc_id = ""
                        applicant = ""
                        product_name = ""
                        
                        # Look for FCC ID in first few cells
                        for i, cell in enumerate(cells[:3]):
                            text = cell.get_text(strip=True)
                            
                            # FCC ID pattern: letters + numbers, usually with dash
                            if i == 0 and len(text) > 5 and any(c.isalpha() for c in text):
                                fcc_id = text
                            elif i == 1:
                                applicant = text
                            elif i == 2:
                                product_name = text
                        
                        if fcc_id:
                            filing = {
                                'fcc_id': fcc_id,
                                'applicant': applicant,
                                'product_name': product_name,
                                'filing_date': datetime.now(),
                                'detail_url': f"https://apps.fcc.gov/oetcf/eas/reports/ViewExhibitReport.cfm?mode=Exhibits&RequestTimeout=500&calledFromFrame=N&application_id={fcc_id}"
                            }
                            filings.append(filing)
                            logger.info(f"Found filing: {fcc_id} - {applicant}")
                
                break  # Found the results table
        
        return filings
    
    def get_filing_details(self, fcc_id: str) -> Optional[Dict]:
        """Get detailed filing information including PDFs"""
        if not self.driver:
            return None
        
        try:
            detail_url = f"https://apps.fcc.gov/oetcf/eas/reports/ViewExhibitReport.cfm?mode=Exhibits&RequestTimeout=500&calledFromFrame=N&application_id={fcc_id}"
            
            logger.info(f"Getting details for {fcc_id}")
            self.driver.get(detail_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Extract PDF links
            pdfs = []
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                filename = link.get_text(strip=True)
                
                if href and '.pdf' in href.lower():
                    # Check if this looks like an internal photos PDF
                    if any(keyword in filename.lower() for keyword in ['internal', 'int', 'photo', 'inside']):
                        full_url = self._build_full_url(href)
                        pdfs.append({
                            'filename': filename,
                            'url': full_url,
                            'fcc_id': fcc_id
                        })
                        logger.info(f"Found internal photos PDF: {filename}")
            
            if pdfs:
                return {
                    'fcc_id': fcc_id,
                    'pdfs': pdfs
                }
            else:
                logger.info(f"No internal photos found for {fcc_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting details for {fcc_id}: {e}")
            return None
    
    def _build_full_url(self, href: str) -> str:
        """Build full URL from relative href"""
        if href.startswith('http'):
            return href
        elif href.startswith('/'):
            return 'https://apps.fcc.gov' + href
        else:
            return f"https://apps.fcc.gov/oetcf/eas/reports/{href}"
    
    def close(self):
        """Close the browser driver"""
        if self.driver:
            self.driver.quit()
            logger.info("Chrome driver closed")
    
    def __del__(self):
        """Cleanup driver on object destruction"""
        self.close()