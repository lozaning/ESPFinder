#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup

def inspect_fcc_form():
    """Inspect the actual FCC form to find correct field names"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    url = "https://apps.fcc.gov/oetcf/eas/reports/GenericSearch.cfm"
    
    try:
        response = session.get(url, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all input fields
            inputs = soup.find_all('input')
            
            print(f"\nFound {len(inputs)} input fields:")
            for input_field in inputs:
                name = input_field.get('name', '')
                input_type = input_field.get('type', '')
                value = input_field.get('value', '')
                
                if name:
                    print(f"  Name: {name}, Type: {input_type}, Value: {value}")
                    
                    # Look for date-related fields
                    if 'date' in name.lower() or 'final' in name.lower():
                        print(f"    *** DATE FIELD FOUND: {name} ***")
            
            # Find all select fields
            selects = soup.find_all('select')
            print(f"\nFound {len(selects)} select fields:")
            for select_field in selects:
                name = select_field.get('name', '')
                if name:
                    print(f"  Select: {name}")
                    
            # Look for any text containing "date"
            all_text = soup.get_text()
            lines_with_date = [line.strip() for line in all_text.split('\n') if 'date' in line.lower() and line.strip()]
            
            print(f"\nLines mentioning 'date':")
            for line in lines_with_date[:10]:  # First 10 matches
                print(f"  {line}")
                
        else:
            print(f"Failed to access FCC page: {response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_fcc_form()