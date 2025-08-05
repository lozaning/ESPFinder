#!/usr/bin/env python3

import http.server
import socketserver
import os
import threading
import time

class PDFHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="data/sample_pdfs", **kwargs)
    
    def log_message(self, format, *args):
        # Suppress log messages
        pass

def start_pdf_server(port=8000):
    """Start a simple HTTP server to serve sample PDFs"""
    
    if not os.path.exists("data/sample_pdfs"):
        print("❌ Sample PDFs directory not found. Run create_sample_pdfs.py first.")
        return None
    
    try:
        with socketserver.TCPServer(("", port), PDFHandler) as httpd:
            print(f"✅ PDF server started at http://localhost:{port}")
            print("Available PDFs:")
            for filename in os.listdir("data/sample_pdfs"):
                if filename.endswith('.pdf'):
                    print(f"  http://localhost:{port}/{filename}")
            
            # Run server in background thread
            server_thread = threading.Thread(target=httpd.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            return httpd
    except Exception as e:
        print(f"❌ Failed to start PDF server: {e}")
        return None

if __name__ == "__main__":
    server = start_pdf_server()
    if server:
        try:
            print("\n🔄 PDF server running. Press Ctrl+C to stop.")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping PDF server...")
            server.shutdown()
            print("✅ PDF server stopped.")