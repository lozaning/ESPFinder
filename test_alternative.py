#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
import json

def test_fccid_dot_io():
    """Test fccid.io website (not API, but web scraping)"""
    print("=== Testing fccid.io website ===")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    # Try searching fccid.io directly
    search_url = "https://fccid.io/search.php"
    
    params = {
        'q': 'internal photos',
        'sort': 'date'
    }
    
    try:
        response = session.get(search_url, params=params, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for FCC ID links
            fcc_links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # fccid.io uses URLs like /2AIZR-2448/
                if href.startswith('/') and len(href.split('/')[1]) >= 7:
                    fcc_id = href.split('/')[1]
                    if fcc_id and '-' in fcc_id:  # Valid FCC ID format
                        fcc_links.append(fcc_id)
            
            print(f"Found {len(fcc_links)} potential FCC IDs")
            
            # Test a few
            for fcc_id in fcc_links[:3]:
                print(f"\nTesting {fcc_id} on fccid.io...")
                detail_url = f"https://fccid.io/{fcc_id}"
                
                try:
                    detail_response = session.get(detail_url, timeout=15)
                    if detail_response.status_code == 200:
                        detail_soup = BeautifulSoup(detail_response.content, 'html.parser')
                        
                        # Look for internal photos
                        internal_links = []
                        for link in detail_soup.find_all('a', href=True):
                            link_text = link.get_text(strip=True).lower()
                            if 'internal' in link_text and 'photo' in link_text:
                                internal_links.append(link.get_text(strip=True))
                        
                        if internal_links:
                            print(f"  ✅ Found internal photos: {len(internal_links)} links")
                            return True
                        else:
                            print(f"  ❌ No internal photos found")
                    else:
                        print(f"  ⚠️  HTTP {detail_response.status_code}")
                        
                except Exception as e:
                    print(f"  💥 Error: {e}")
            
        return False
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_create_sample_data():
    """Create sample data for testing the rest of the system"""
    print("\n=== Creating sample data for testing ===")
    
    # Create some fake but realistic FCC data
    sample_filings = [
        {
            'fcc_id': 'TEST-001',
            'applicant': 'Test Electronics Corp',
            'product_name': 'Wireless Router',
            'filing_date': '2025-08-01',
            'pdfs': [
                {
                    'filename': 'Internal_Photos.pdf',
                    'url': 'https://example.com/internal_photos.pdf'
                }
            ]
        },
        {
            'fcc_id': 'TEST-002', 
            'applicant': 'Sample Tech Inc',
            'product_name': 'Bluetooth Speaker',
            'filing_date': '2025-08-02',
            'pdfs': [
                {
                    'filename': 'Int_Photos_Report.pdf',
                    'url': 'https://example.com/int_photos.pdf'
                }
            ]
        }
    ]
    
    print("Sample filings created:")
    for filing in sample_filings:
        print(f"  {filing['fcc_id']}: {filing['product_name']} by {filing['applicant']}")
        for pdf in filing['pdfs']:
            print(f"    - {pdf['filename']}")
    
    return sample_filings

def test_fcc_official_alternative():
    """Try FCC's main search page"""
    print("\n=== Testing FCC official search ===")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    # Try the main FCC search
    search_url = "https://www.fcc.gov/oet/ea/fccid"
    
    try:
        response = session.get(search_url, timeout=30)
        print(f"FCC main search page: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ FCC main site is accessible")
            return True
        else:
            print("❌ FCC main site failed")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success1 = test_fccid_dot_io()
    success2 = test_fcc_official_alternative()
    
    if not (success1 or success2):
        print("\n🔄 FCC data sources unavailable - creating sample data for testing")
        sample_data = test_create_sample_data()
        
        print("\n💡 SOLUTION: Use sample data to test the system end-to-end")
        print("   Once FCC is working again, we can switch back to real data")
        
    else:
        print("\n✅ Found working data source!")