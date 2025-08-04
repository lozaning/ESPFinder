import os
import requests
import fitz
import time
from PIL import Image
from typing import List, Dict, Optional
import structlog

from ..config import Config
from ..database.database import db
from ..database.models import PDF, Photo

logger = structlog.get_logger()

class PDFProcessor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def download_pdf(self, pdf: PDF) -> bool:
        if pdf.downloaded and pdf.local_path and os.path.exists(pdf.local_path):
            return True
            
        try:
            response = self.session.get(pdf.url, timeout=60)
            response.raise_for_status()
            
            pdf_dir = os.path.join(Config.IMAGES_DIR, pdf.product.fcc_id)
            os.makedirs(pdf_dir, exist_ok=True)
            
            safe_filename = self._sanitize_filename(pdf.filename)
            local_path = os.path.join(pdf_dir, safe_filename)
            
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            session = db.get_session()
            try:
                pdf.local_path = local_path
                pdf.downloaded = True
                pdf.file_size = len(response.content)
                session.commit()
                
                logger.info(f"Downloaded PDF: {pdf.filename} ({pdf.file_size} bytes)")
                return True
                
            except Exception as e:
                session.rollback()
                logger.error(f"Error updating PDF record: {e}")
                return False
            finally:
                session.close()
                
            time.sleep(Config.DOWNLOAD_DELAY)
            
        except Exception as e:
            logger.error(f"Error downloading PDF {pdf.filename}: {e}")
            return False
    
    def extract_images_from_pdf(self, pdf: PDF) -> List[Photo]:
        if not pdf.local_path or not os.path.exists(pdf.local_path):
            logger.error(f"PDF file not found: {pdf.local_path}")
            return []
        
        try:
            doc = fitz.open(pdf.local_path)
            extracted_photos = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    photo = self._extract_image(doc, img, pdf, page_num, img_index)
                    if photo:
                        extracted_photos.append(photo)
            
            doc.close()
            
            session = db.get_session()
            try:
                pdf.processed = True
                session.commit()
                logger.info(f"Extracted {len(extracted_photos)} images from {pdf.filename}")
            except Exception as e:
                session.rollback()
                logger.error(f"Error updating PDF processed status: {e}")
            finally:
                session.close()
            
            return extracted_photos
            
        except Exception as e:
            logger.error(f"Error extracting images from PDF {pdf.filename}: {e}")
            return []
    
    def _extract_image(self, doc: fitz.Document, img, pdf: PDF, page_num: int, img_index: int) -> Optional[Photo]:
        try:
            xref = img[0]
            pix = fitz.Pixmap(doc, xref)
            
            if pix.n - pix.alpha < 4:  # Skip if not RGB/RGBA
                img_data = pix.tobytes("png")
                pix = None
                
                image_dir = os.path.join(Config.IMAGES_DIR, pdf.product.fcc_id)
                os.makedirs(image_dir, exist_ok=True)
                
                filename = f"page_{page_num+1}_img_{img_index+1}.png"
                image_path = os.path.join(image_dir, filename)
                
                with open(image_path, "wb") as img_file:
                    img_file.write(img_data)
                
                pil_img = Image.open(image_path)
                width, height = pil_img.size
                file_size = os.path.getsize(image_path)
                
                if self._is_valid_image(pil_img):
                    photo = Photo(
                        product_id=pdf.product_id,
                        pdf_id=pdf.id,
                        filename=filename,
                        local_path=image_path,
                        width=width,
                        height=height,
                        file_size=file_size,
                        page_number=page_num + 1
                    )
                    
                    session = db.get_session()
                    try:
                        session.add(photo)
                        session.commit()
                        return photo
                    except Exception as e:
                        session.rollback()
                        logger.error(f"Error saving photo to database: {e}")
                        return None
                    finally:
                        session.close()
                else:
                    os.remove(image_path)
                    return None
            else:
                if pix:
                    pix = None
                return None
                
        except Exception as e:
            logger.error(f"Error extracting image {img_index} from page {page_num}: {e}")
            return None
    
    def _is_valid_image(self, img: Image.Image) -> bool:
        min_width, min_height = 100, 100
        max_width, max_height = 5000, 5000
        
        width, height = img.size
        
        if width < min_width or height < min_height:
            return False
        if width > max_width or height > max_height:
            return False
            
        aspect_ratio = width / height
        if aspect_ratio > 10 or aspect_ratio < 0.1:
            return False
            
        return True
    
    def _sanitize_filename(self, filename: str) -> str:
        import re
        filename = re.sub(r'[^\w\-_\.]', '_', filename)
        return filename[:200]  # Limit filename length
    
    def process_unprocessed_pdfs(self) -> int:
        session = db.get_session()
        try:
            unprocessed_pdfs = session.query(PDF).filter_by(processed=False).all()
            processed_count = 0
            
            for pdf in unprocessed_pdfs:
                if self.download_pdf(pdf):
                    photos = self.extract_images_from_pdf(pdf)
                    if photos:
                        processed_count += 1
                        
            return processed_count
            
        finally:
            session.close()