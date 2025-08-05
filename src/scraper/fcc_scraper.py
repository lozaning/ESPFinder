import requests
import re
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import structlog

from ..config import Config
from ..database.database import db
from ..database.models import Product, PDF

logger = structlog.get_logger()

class FCCScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def search_recent_filings(self, days_back: int = 7) -> List[Dict]:
        # Try multiple FCC endpoints in case the original is down
        search_urls = [
            "https://fccid.io/api/search",  # Alternative FCC database
            "https://apps.fcc.gov/oetcf/eas/reports/ViewExhibitReport.cfm",  # Original
            f"{Config.FCC_BASE_URL}/ViewExhibitReport.cfm"  # Fallback
        ]
        
        for search_url in search_urls:
            try:
                logger.info(f"Trying FCC endpoint: {search_url}")
                
                if "fccid.io" in search_url:
                    # Use fccid.io API as alternative
                    filings = self._search_fccid_io()
                else:
                    # Use original FCC site
                    params = {
                        'mode': 'Exhibits',
                        'RequestTimeout': '500',
                        'calledFromFrame': 'N'
                    }
                    
                    response = self.session.get(search_url, params=params, timeout=30)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    filings = self._parse_search_results(soup)
                
                logger.info(f"Found {len(filings)} recent filings from {search_url}")
                return filings
                
            except Exception as e:
                logger.warning(f"Failed to access {search_url}: {e}")
                continue
        
        logger.error("All FCC endpoints failed")
        return []
    
    def _search_fccid_io(self) -> List[Dict]:
        """Alternative search using fccid.io API"""
        try:
            # Search for recent filings with photos
            response = self.session.get("https://fccid.io/api/search?q=internal+photos&limit=20", timeout=30)
            response.raise_for_status()
            
            data = response.json()
            filings = []
            
            for item in data.get('results', []):
                if item.get('fcc_id'):
                    filing = {
                        'fcc_id': item['fcc_id'],
                        'applicant': item.get('applicant_name', ''),
                        'product_name': item.get('product_name', ''),
                        'filing_date': self._parse_date(item.get('date_received', '')),
                        'detail_url': f"https://fccid.io/{item['fcc_id']}"
                    }
                    filings.append(filing)
            
            return filings
            
        except Exception as e:
            logger.error(f"Error with fccid.io API: {e}")
            return []
    
    def _parse_search_results(self, soup: BeautifulSoup) -> List[Dict]:
        filings = []
        
        for row in soup.find_all('tr')[1:]:  # Skip header row
            cells = row.find_all('td')
            if len(cells) >= 4:
                fcc_id_cell = cells[0]
                fcc_id = fcc_id_cell.get_text(strip=True)
                
                if fcc_id:
                    filing = {
                        'fcc_id': fcc_id,
                        'applicant': cells[1].get_text(strip=True),
                        'product_name': cells[2].get_text(strip=True),
                        'filing_date': self._parse_date(cells[3].get_text(strip=True)),
                        'detail_url': self._extract_detail_url(fcc_id_cell)
                    }
                    filings.append(filing)
                    
        return filings
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        try:
            return datetime.strptime(date_str.strip(), '%m/%d/%Y')
        except:
            return None
    
    def _extract_detail_url(self, cell) -> Optional[str]:
        link = cell.find('a')
        if link and link.get('href'):
            return Config.FCC_BASE_URL + "/" + link['href']
        return None
    
    def get_filing_details(self, fcc_id: str) -> Optional[Dict]:
        detail_url = f"{Config.FCC_BASE_URL}/ViewExhibitReport.cfm?mode=Exhibits&RequestTimeout=500&calledFromFrame=N&application_id={fcc_id}"
        
        try:
            response = self.session.get(detail_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            details = {
                'fcc_id': fcc_id,
                'pdfs': self._extract_pdf_links(soup, fcc_id)
            }
            
            time.sleep(Config.DOWNLOAD_DELAY)
            return details
            
        except Exception as e:
            logger.error(f"Error getting details for {fcc_id}: {e}")
            return None
    
    def _extract_pdf_links(self, soup: BeautifulSoup, fcc_id: str) -> List[Dict]:
        pdf_links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            filename = link.get_text(strip=True)
            
            if href.endswith('.pdf') and self._is_internal_photo_pdf(filename):
                full_url = self._build_full_url(href)
                pdf_links.append({
                    'filename': filename,
                    'url': full_url,
                    'fcc_id': fcc_id
                })
                
        return pdf_links
    
    def _is_internal_photo_pdf(self, filename: str) -> bool:
        for pattern in Config.PDF_FILENAME_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                return True
        return False
    
    def _build_full_url(self, href: str) -> str:
        if href.startswith('http'):
            return href
        elif href.startswith('/'):
            return 'https://apps.fcc.gov' + href
        else:
            return f"{Config.FCC_BASE_URL}/{href}"
    
    def save_to_database(self, filing_data: Dict) -> Optional[Product]:
        session = db.get_session()
        
        try:
            existing = session.query(Product).filter_by(fcc_id=filing_data['fcc_id']).first()
            if existing:
                logger.info(f"Product {filing_data['fcc_id']} already exists")
                return existing
            
            product = Product(
                fcc_id=filing_data['fcc_id'],
                applicant=filing_data.get('applicant'),
                product_name=filing_data.get('product_name'),
                filing_date=filing_data.get('filing_date')
            )
            
            session.add(product)
            session.flush()
            
            for pdf_data in filing_data.get('pdfs', []):
                pdf = PDF(
                    product_id=product.id,
                    filename=pdf_data['filename'],
                    url=pdf_data['url']
                )
                session.add(pdf)
            
            session.commit()
            logger.info(f"Saved product {product.fcc_id} with {len(filing_data.get('pdfs', []))} PDFs")
            return product
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving to database: {e}")
            return None
        finally:
            session.close()