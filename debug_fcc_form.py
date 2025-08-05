#!/usr/bin/env python3

import sys
import os
sys.path.append('/home/lozaning/ESPFinder')

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time

def debug_fcc_form():
    """Debug the FCC GenericSearch form submission process"""
    
    # Setup headless Chrome
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument(f'--user-data-dir=/tmp/chrome-debug-{int(time.time())}')
    
    driver = None
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("✅ Chrome driver initialized")
        
        # Navigate to FCC search page
        url = "https://apps.fcc.gov/oetcf/eas/reports/GenericSearch.cfm"
        print(f"🌐 Navigating to: {url}")
        driver.get(url)
        
        # Wait for page to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "form"))
        )
        print("✅ Page loaded, form found")
        
        # Debug: Find all input fields
        inputs = driver.find_elements(By.TAG_NAME, "input")
        print(f"\n📝 Found {len(inputs)} input fields:")
        for i, inp in enumerate(inputs[:20]):  # Show first 20
            name = inp.get_attribute('name') or 'No name'
            input_type = inp.get_attribute('type') or 'No type'
            value = inp.get_attribute('value') or 'No value'
            print(f"  {i+1}. name='{name}' type='{input_type}' value='{value}'")
        
        # Look for date fields
        print(f"\n📅 Looking for date fields...")
        date_fields = ['grant_date_from', 'grant_date_to', 'final_start_date', 'final_end_date', 'start_date', 'end_date']
        found_fields = []
        
        for field_name in date_fields:
            try:
                field = driver.find_element(By.NAME, field_name)
                found_fields.append(field_name)
                print(f"  ✅ Found: {field_name}")
            except NoSuchElementException:
                print(f"  ❌ Not found: {field_name}")
        
        if not found_fields:
            print("❌ No date fields found with expected names")
            # Save page source for debugging
            with open('/tmp/fcc_debug.html', 'w') as f:
                f.write(driver.page_source)
            print("💾 Saved page source to /tmp/fcc_debug.html")
            return
        
        # Use yesterday's date
        yesterday = datetime.now() - timedelta(days=1)
        date_str = yesterday.strftime('%m/%d/%Y')
        print(f"📅 Using date: {date_str}")
        
        # Fill in the first available date field
        field_name = found_fields[0]
        try:
            start_field = driver.find_element(By.NAME, field_name)
            start_field.clear()
            start_field.send_keys(date_str)
            print(f"✅ Filled {field_name} with {date_str}")
            
            # If there's a second date field, fill it too
            if len(found_fields) > 1:
                end_field_name = found_fields[1]
                end_field = driver.find_element(By.NAME, end_field_name)
                end_field.clear()
                end_field.send_keys(date_str)
                print(f"✅ Filled {end_field_name} with {date_str}")
        
        except Exception as e:
            print(f"❌ Error filling date fields: {e}")
            return
        
        # Look for submit buttons
        print(f"\n🔍 Looking for submit elements...")
        submit_elements = []
        
        # Check input[type=submit]
        submit_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='submit']")
        for inp in submit_inputs:
            name = inp.get_attribute('name') or 'No name'
            value = inp.get_attribute('value') or 'No value'
            submit_elements.append(f"input[type=submit] name='{name}' value='{value}'")
        
        # Check buttons
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            name = btn.get_attribute('name') or 'No name'
            text = btn.text or 'No text'
            submit_elements.append(f"button name='{name}' text='{text}'")
        
        # Check input[name=Submit]
        try:
            submit_by_name = driver.find_element(By.NAME, "Submit")
            submit_elements.append("input[name='Submit'] found")
        except:
            pass
        
        print(f"Submit elements found: {len(submit_elements)}")
        for elem in submit_elements:
            print(f"  - {elem}")
        
        if not submit_elements:
            print("❌ No submit elements found")
            return
        
        # Try to submit the form
        print(f"\n🚀 Attempting form submission...")
        try:
            # Try the most common submit button
            submit_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
            submit_button.click()
            print("✅ Form submitted")
            
            # Wait for results to load
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            print("✅ Results page loaded")
            
            # Parse results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            tables = soup.find_all('table')
            print(f"📊 Found {len(tables)} tables on results page")
            
            # Look for results table
            for i, table in enumerate(tables):
                rows = table.find_all('tr')
                if len(rows) > 1:  # Has data rows
                    print(f"\n📋 Table {i+1} has {len(rows)} rows")
                    
                    # Show first few rows
                    for j, row in enumerate(rows[:3]):
                        cells = row.find_all(['td', 'th'])
                        cell_texts = [cell.get_text(strip=True)[:30] for cell in cells]
                        print(f"  Row {j+1}: {cell_texts}")
                    
                    # Look for FCC ID links
                    links = table.find_all('a', href=True)
                    print(f"  🔗 Found {len(links)} links in this table")
                    
                    detail_links = []
                    for link in links[:5]:  # Show first 5 links
                        href = link.get('href')
                        text = link.get_text(strip=True)
                        print(f"    - '{text}' -> {href}")
                        
                        # Check if this looks like a detail page link
                        if 'ViewExhibitReport' in href or 'application_id' in href:
                            detail_links.append((text, href))
                    
                    if detail_links:
                        print(f"  ✅ Found {len(detail_links)} potential detail page links")
                        
                        # Test the first detail link
                        fcc_id, detail_href = detail_links[0]
                        print(f"\n🔍 Testing detail page for {fcc_id}")
                        
                        full_detail_url = detail_href
                        if not detail_href.startswith('http'):
                            if detail_href.startswith('/'):
                                full_detail_url = 'https://apps.fcc.gov' + detail_href
                            else:
                                full_detail_url = f'https://apps.fcc.gov/oetcf/eas/reports/{detail_href}'
                        
                        print(f"🌐 Detail URL: {full_detail_url}")
                        
                        # Navigate to detail page
                        driver.get(full_detail_url)
                        time.sleep(3)
                        
                        # Look for PDF links
                        detail_soup = BeautifulSoup(driver.page_source, 'html.parser')
                        pdf_links = detail_soup.find_all('a', href=True)
                        
                        internal_pdfs = []
                        for link in pdf_links:
                            href = link.get('href')
                            text = link.get_text(strip=True)
                            
                            if '.pdf' in href.lower():
                                # Check if this looks like internal photos
                                if any(keyword in text.lower() for keyword in ['internal', 'int', 'photo', 'inside']):
                                    internal_pdfs.append((text, href))
                        
                        print(f"📄 Found {len(internal_pdfs)} potential internal photo PDFs:")
                        for pdf_text, pdf_href in internal_pdfs:
                            print(f"  - '{pdf_text}' -> {pdf_href}")
                        
                        break  # Found results table, stop looking
            
        except Exception as e:
            print(f"❌ Error during form submission: {e}")
            with open('/tmp/fcc_submit_debug.html', 'w') as f:
                f.write(driver.page_source)
            print("💾 Saved page source to /tmp/fcc_submit_debug.html")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if driver:
            driver.quit()
            print("🔒 Driver closed")

if __name__ == "__main__":
    print("🔧 Debugging FCC form submission process...")
    debug_fcc_form()
    print("✅ Debug completed")