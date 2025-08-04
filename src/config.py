import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/database/espfinder.db')
    
    DATA_DIR = os.getenv('DATA_DIR', 'data')
    IMAGES_DIR = os.path.join(DATA_DIR, 'images')
    DATABASE_DIR = os.path.join(DATA_DIR, 'database')
    
    FCC_BASE_URL = "https://apps.fcc.gov/oetcf/eas/reports"
    
    DOWNLOAD_DELAY = float(os.getenv('DOWNLOAD_DELAY', '1.0'))
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    
    PDF_FILENAME_PATTERNS = [
        r'.*internal.*photo.*\.pdf',
        r'.*int.*photo.*\.pdf',
        r'.*inside.*\.pdf',
        r'.*pcb.*\.pdf',
        r'.*internal.*\.pdf'
    ]
    
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def ensure_dirs(cls):
        os.makedirs(cls.IMAGES_DIR, exist_ok=True)
        os.makedirs(cls.DATABASE_DIR, exist_ok=True)