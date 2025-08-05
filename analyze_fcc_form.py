#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def analyze_fcc_form():
    """Analyze the FCC GenericSearch form structure"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    
    try:
        print("🌐 Fetching FCC GenericSearch form (90s timeout for slow government site)...")
        url = "https://apps.fcc.gov/oetcf/eas/reports/GenericSearch.cfm"
        response = session.get(url, timeout=90)
        response.raise_for_status()
        
        print(f"✅ Form loaded (status: {response.status_code})")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all forms
        forms = soup.find_all('form')
        print(f"📝 Found {len(forms)} forms")
        
        for i, form in enumerate(forms):
            print(f"\n--- Form {i+1} ---")
            action = form.get('action', 'No action')
            method = form.get('method', 'GET')
            print(f"Action: {action}")
            print(f"Method: {method}")
            
            # Find all input fields in this form
            inputs = form.find_all('input')
            print(f"Input fields: {len(inputs)}")
            
            for inp in inputs:
                name = inp.get('name', 'No name')
                input_type = inp.get('type', 'text')
                value = inp.get('value', '')
                placeholder = inp.get('placeholder', '')
                
                print(f"  {name} [{input_type}] = '{value}' placeholder='{placeholder}'")
            
            # Find select fields
            selects = form.find_all('select')
            if selects:
                print(f"Select fields: {len(selects)}")
                for sel in selects:
                    name = sel.get('name', 'No name')
                    options = [opt.get('value', '') for opt in sel.find_all('option')]
                    print(f"  {name} options: {options[:5]}...")  # Show first 5 options
            
            # Find textareas
            textareas = form.find_all('textarea')
            if textareas:
                print(f"Textarea fields: {len(textareas)}")
                for ta in textareas:
                    name = ta.get('name', 'No name')
                    print(f"  {name}")
        
        # Look for date-related fields specifically
        print(f"\n📅 Looking for date-related fields...")
        date_keywords = ['date', 'start', 'end', 'from', 'to', 'final', 'grant']
        
        all_inputs = soup.find_all('input')
        date_fields = []
        
        for inp in all_inputs:
            name = inp.get('name', '')
            if name and any(keyword in name.lower() for keyword in date_keywords):
                input_type = inp.get('type', 'text')
                date_fields.append((name, input_type))
        
        print(f"Found {len(date_fields)} potential date fields:")
        for name, field_type in date_fields:
            print(f"  - {name} [{field_type}]")
        
        # Look for submit buttons
        print(f"\n🚀 Looking for submit elements...")
        submit_inputs = soup.find_all('input', {'type': 'submit'})
        buttons = soup.find_all('button')
        
        print(f"Submit inputs: {len(submit_inputs)}")
        for inp in submit_inputs:
            name = inp.get('name', 'No name')
            value = inp.get('value', 'No value')
            print(f"  - name='{name}' value='{value}'")
        
        print(f"Buttons: {len(buttons)}")
        for btn in buttons:
            name = btn.get('name', 'No name')
            text = btn.get_text(strip=True)
            btn_type = btn.get('type', 'button')
            print(f"  - name='{name}' type='{btn_type}' text='{text}'")
        
        # Try to understand the form structure for date submission
        print(f"\n📋 Form submission analysis:")
        
        if date_fields:
            # Use yesterday's date for testing
            yesterday = datetime.now() - timedelta(days=1)
            date_str = yesterday.strftime('%m/%d/%Y')
            print(f"Test date: {date_str}")
            
            # Build form data for testing
            form_data = {}
            
            # Add date fields
            for name, field_type in date_fields:
                if 'start' in name.lower() or 'from' in name.lower():
                    form_data[name] = date_str
                    print(f"  Would set {name} = {date_str}")
                elif 'end' in name.lower() or 'to' in name.lower():
                    form_data[name] = date_str 
                    print(f"  Would set {name} = {date_str}")
            
            print(f"\nForm data for submission: {form_data}")
            
            # Try to submit the form
            if forms and form_data:
                form = forms[0]  # Use first form
                action = form.get('action', 'GenericSearch.cfm')
                method = form.get('method', 'GET').upper()
                
                # Build full action URL
                if not action.startswith('http'):
                    if action.startswith('/'):
                        action_url = 'https://apps.fcc.gov' + action
                    else:
                        action_url = f'https://apps.fcc.gov/oetcf/eas/reports/{action}'
                else:
                    action_url = action
                
                print(f"\n🚀 Testing form submission:")
                print(f"URL: {action_url}")
                print(f"Method: {method}")
                print(f"Data: {form_data}")
                
                try:
                    if method == 'GET':
                        response = session.get(action_url, params=form_data, timeout=120)
                    else:
                        response = session.post(action_url, data=form_data, timeout=120)
                    
                    print(f"✅ Form submitted (status: {response.status_code})")
                    
                    if response.status_code == 200:
                        # Parse results
                        results_soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Look for results tables
                        tables = results_soup.find_all('table')
                        print(f"📊 Results page has {len(tables)} tables")
                        
                        for i, table in enumerate(tables):
                            rows = table.find_all('tr')
                            if len(rows) > 1:  # Has data
                                print(f"\nTable {i+1}: {len(rows)} rows")
                                
                                # Show first few rows
                                for j, row in enumerate(rows[:3]):
                                    cells = row.find_all(['td', 'th'])
                                    texts = [cell.get_text(strip=True)[:40] for cell in cells[:5]]
                                    print(f"  Row {j+1}: {texts}")
                                
                                # Look for links to detail pages
                                links = table.find_all('a', href=True)
                                detail_links = []
                                
                                for link in links:
                                    href = link.get('href')
                                    text = link.get_text(strip=True)
                                    
                                    # Check if this looks like a detail page link
                                    if ('ViewExhibitReport' in href or 
                                        'application_id' in href or
                                        'RequestTimeout' in href):
                                        detail_links.append((text, href))
                                
                                if detail_links:
                                    print(f"  🔗 Found {len(detail_links)} detail page links:")
                                    for text, href in detail_links[:3]:  # Show first 3
                                        print(f"    - '{text}' -> {href[:80]}...")
                                    
                                    # Test first detail link
                                    if detail_links:
                                        test_fcc_id, test_href = detail_links[0]
                                        print(f"\n🔍 Testing detail page for: {test_fcc_id}")
                                        
                                        # Build full URL
                                        if not test_href.startswith('http'):
                                            if test_href.startswith('/'):
                                                detail_url = 'https://apps.fcc.gov' + test_href
                                            else:
                                                detail_url = f'https://apps.fcc.gov/oetcf/eas/reports/{test_href}'
                                        else:
                                            detail_url = test_href
                                        
                                        print(f"Detail URL: {detail_url}")
                                        
                                        # Fetch detail page
                                        detail_response = session.get(detail_url, timeout=30)
                                        if detail_response.status_code == 200:
                                            detail_soup = BeautifulSoup(detail_response.content, 'html.parser')
                                            
                                            # Look for PDF links
                                            pdf_links = detail_soup.find_all('a', href=True)
                                            internal_pdfs = []
                                            
                                            for link in pdf_links:
                                                href = link.get('href')
                                                text = link.get_text(strip=True)
                                                
                                                if '.pdf' in href.lower():
                                                    # Check for internal photos keywords
                                                    keywords = ['internal', 'int', 'photo', 'inside', 'pcb']
                                                    if any(kw in text.lower() for kw in keywords):
                                                        internal_pdfs.append((text, href))
                                            
                                            print(f"📄 Found {len(internal_pdfs)} internal photo PDFs:")
                                            for pdf_text, pdf_href in internal_pdfs:
                                                print(f"  - '{pdf_text}' -> {pdf_href}")
                                        else:
                                            print(f"❌ Detail page failed: {detail_response.status_code}")
                                
                                break  # Found a results table
                    
                except Exception as e:
                    print(f"❌ Form submission failed: {e}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🔧 Analyzing FCC GenericSearch form...")
    analyze_fcc_form()
    print("✅ Analysis completed")