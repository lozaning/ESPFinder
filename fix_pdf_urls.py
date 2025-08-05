#!/usr/bin/env python3

import sys
import os
sys.path.append('/home/lozaning/ESPFinder')

from src.database.database import db
from src.database.models import PDF

def fix_sample_pdf_urls():
    """Update sample PDF URLs to use correct local serving endpoints"""
    
    session = db.get_session()
    
    try:
        # Get all PDFs with example.com URLs (old sample URLs)
        old_pdfs = session.query(PDF).filter(PDF.url.like('%example.com%')).all()
        
        print(f"Found {len(old_pdfs)} PDFs with old URLs to fix")
        
        for pdf in old_pdfs:
            old_url = pdf.url
            
            # Extract FCC ID from the product relationship
            fcc_id = pdf.product.fcc_id if pdf.product else 'UNKNOWN'
            
            # Build new URL using the Flask route
            if 'internal' in pdf.filename.lower():
                new_url = f'http://espfinder-web:5000/sample_pdfs/{fcc_id}_Internal_Photos.pdf'
            elif 'test' in pdf.filename.lower():
                new_url = f'http://espfinder-web:5000/sample_pdfs/{fcc_id}_Test_Report.pdf'
            else:
                # Generic fallback
                new_url = f'http://espfinder-web:5000/sample_pdfs/{pdf.filename}'
            
            print(f"Updating PDF {pdf.id}: {old_url} -> {new_url}")
            pdf.url = new_url
            
            # Reset download/process flags so they get retried
            pdf.downloaded = False
            pdf.processed = False
        
        session.commit()
        print(f"✅ Successfully updated {len(old_pdfs)} PDF URLs")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error updating PDF URLs: {e}")
        return False
    finally:
        session.close()
    
    return True

if __name__ == "__main__":
    print("🔧 Fixing sample PDF URLs...")
    
    if fix_sample_pdf_urls():
        print("✅ PDF URL fix completed successfully")
    else:
        print("❌ PDF URL fix failed")