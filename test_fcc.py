#!/usr/bin/env python3

import requests
import json
from bs4 import BeautifulSoup

def test_fcc_endpoints():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    # Test different FCC endpoints
    endpoints = [
        "https://fccid.io/api/search?q=internal+photos&limit=5",
        "https://www.fcc.gov/oet/ea/fccid",
        "https://apps.fcc.gov/oetcf/eas/reports/GenericSearch.cfm",
        "https://apps.fcc.gov/oetcf/eas/reports/ViewExhibitReport.cfm?mode=Exhibits&RequestTimeout=500&calledFromFrame=N"
    ]
    
    for url in endpoints:
        try:
            print(f"\n=== TESTING: {url} ===")
            response = session.get(url, timeout=10)
            print(f"Status: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type', 'unknown')}")
            
            content = response.text[:500]
            print(f"Content preview: {content}")
            
            if 'json' in response.headers.get('content-type', ''):
                try:
                    data = response.json()
                    print(f"JSON keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                except:
                    print("Failed to parse JSON")
                    
        except Exception as e:
            print(f"ERROR: {e}")

if __name__ == "__main__":
    test_fcc_endpoints()