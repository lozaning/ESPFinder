import os
from dotenv import load_dotenv

# Try to load .env file if it exists (for Docker/local dev)
# In LXC deployment, env vars come from systemd EnvironmentFile
if os.path.exists('.env'):
    load_dotenv()
elif os.path.exists('/opt/espfinder/.env'):
    load_dotenv('/opt/espfinder/.env')

class Config:
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/database/espfinder.db')

    DATA_DIR = os.getenv('DATA_DIR', 'data')
    IMAGES_DIR = os.path.join(DATA_DIR, 'images')
    DATABASE_DIR = os.path.join(DATA_DIR, 'database')
    SAMPLE_PDFS_DIR = os.path.join(DATA_DIR, 'sample_pdfs')

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

    # Deployment mode (Docker or LXC/native)
    IS_DOCKER = os.path.exists('/.dockerenv')

    @classmethod
    def ensure_dirs(cls):
        os.makedirs(cls.IMAGES_DIR, exist_ok=True)
        os.makedirs(cls.DATABASE_DIR, exist_ok=True)
        os.makedirs(cls.SAMPLE_PDFS_DIR, exist_ok=True)