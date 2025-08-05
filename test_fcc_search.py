#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup

def test_working_fcc_search():
    """Test a working FCC search approach"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    # Try the FCC ID search directly - this should work
    print("=== Testing direct FCC ID search ===")
    
    # Use a known FCC ID for testing
    test_fcc_id = "2AIZR-2448"  # Apple device
    
    detail_url = f"https://apps.fcc.gov/oetcf/eas/reports/ViewExhibitReport.cfm?mode=Exhibits&RequestTimeout=500&calledFromFrame=N&application_id={test_fcc_id}"
    
    try:
        response = session.get(detail_url, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for PDF links
            pdf_links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                if '.pdf' in href.lower():
                    pdf_links.append((text, href))
            
            print(f"Found {len(pdf_links)} PDF links:")
            for text, href in pdf_links:
                print(f"  {text}")
                if any(keyword in text.lower() for keyword in ['internal', 'int', 'photo', 'inside']):
                    print(f"    *** INTERNAL PHOTOS FOUND! ***")
            
            return len(pdf_links) > 0
            
        else:
            print(f"Failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_simple_approach():
    """Test simpler approach - use known good FCC IDs"""
    print("\n=== Testing simple approach with known FCC IDs ===")
    
    # Some recent/known FCC IDs to test with
    test_fcc_ids = [
        "2AIZR-2448",   # Apple
        "2AIZR-2449",   # Apple  
        "A94YG2100",    # Google
        "2AC7Z-A2596"   # Microsoft
    ]
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    found_filings = []
    
    for fcc_id in test_fcc_ids:
        print(f"\nTesting {fcc_id}...")
        
        detail_url = f"https://apps.fcc.gov/oetcf/eas/reports/ViewExhibitReport.cfm?mode=Exhibits&RequestTimeout=500&calledFromFrame=N&application_id={fcc_id}"
        
        try:
            response = session.get(detail_url, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Check for internal photo PDFs
                has_internal_photos = False
                pdf_count = 0
                
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    if '.pdf' in href.lower():
                        pdf_count += 1
                        if any(keyword in text.lower() for keyword in ['internal', 'int', 'photo', 'inside']):
                            has_internal_photos = True
                            print(f"  ✅ Found internal photos: {text}")
                
                if has_internal_photos:
                    filing = {
                        'fcc_id': fcc_id,
                        'has_internal_photos': True,
                        'pdf_count': pdf_count
                    }
                    found_filings.append(filing)
                    print(f"  📊 Total PDFs: {pdf_count}")
                else:
                    print(f"  ❌ No internal photos (found {pdf_count} PDFs)")
                    
            else:
                print(f"  ⚠️  HTTP {response.status_code}")
                
        except Exception as e:
            print(f"  💥 Error: {e}")
    
    print(f"\n=== SUMMARY ===")
    print(f"Found {len(found_filings)} FCC IDs with internal photos:")
    for filing in found_filings:
        print(f"  {filing['fcc_id']} - {filing['pdf_count']} PDFs")
    
    return len(found_filings) > 0

if __name__ == "__main__":
    success1 = test_working_fcc_search()
    success2 = test_simple_approach()
    
    if success1 or success2:
        print("\n✅ FCC access is working - can proceed with implementation")
    else:
        print("\n❌ FCC access failed - need different approach")