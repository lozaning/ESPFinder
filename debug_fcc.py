#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup

def debug_fcc_search():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    search_url = "https://apps.fcc.gov/oetcf/eas/reports/GenericSearch.cfm"
    
    params = {
        'mode': 'current',
        'application_status': 'G',  # Granted applications
        'product_type': '',
        'equipment_class': '',
        'display_type': 'summary'
    }
    
    print(f"Testing FCC GenericSearch: {search_url}")
    print(f"Parameters: {params}")
    
    try:
        response = session.get(search_url, params=params, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Content Length: {len(response.content)}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for forms first
            forms = soup.find_all('form')
            print(f"\nFound {len(forms)} forms on the page")
            
            # Look for tables
            tables = soup.find_all('table')
            print(f"Found {len(tables)} tables")
            
            for i, table in enumerate(tables):
                rows = table.find_all('tr')
                print(f"  Table {i+1}: {len(rows)} rows")
                
                if len(rows) > 1:  # Has data rows
                    # Show first few rows
                    for j, row in enumerate(rows[:3]):
                        cells = row.find_all(['td', 'th'])
                        cell_texts = [cell.get_text(strip=True)[:50] for cell in cells]
                        print(f"    Row {j+1}: {cell_texts}")
            
            # Look for any links that might be FCC IDs
            links = soup.find_all('a', href=True)
            fcc_links = []
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                if 'fcc' in href.lower() or len(text) == 10:  # FCC IDs are typically 10 chars
                    fcc_links.append((text, href))
            
            print(f"\nFound {len(fcc_links)} potential FCC links:")
            for text, href in fcc_links[:5]:
                print(f"  {text} -> {href}")
                
        else:
            print(f"Error: HTTP {response.status_code}")
            print(response.text[:500])
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    debug_fcc_search()