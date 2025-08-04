from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base
from ..config import Config

class Database:
    def __init__(self):
        self.engine = create_engine(Config.DATABASE_URL)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self):
        Base.metadata.create_all(bind=self.engine)
        
    def get_session(self):
        return self.SessionLocal()
        
    def close(self):
        self.engine.dispose()

db = Database()