from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    fcc_id = Column(String(50), unique=True, nullable=False, index=True)
    applicant = Column(String(255))
    product_name = Column(String(255))
    product_description = Column(Text)
    filing_date = Column(DateTime)
    grant_date = Column(DateTime)
    equipment_class = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    photos = relationship("Photo", back_populates="product", cascade="all, delete-orphan")
    pdfs = relationship("PDF", back_populates="product", cascade="all, delete-orphan")

class PDF(Base):
    __tablename__ = 'pdfs'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    filename = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    local_path = Column(String(500))
    downloaded = Column(Boolean, default=False)
    processed = Column(Boolean, default=False)
    file_size = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    product = relationship("Product", back_populates="pdfs")
    photos = relationship("Photo", back_populates="pdf", cascade="all, delete-orphan")

class Photo(Base):
    __tablename__ = 'photos'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    pdf_id = Column(Integer, ForeignKey('pdfs.id'), nullable=True)
    filename = Column(String(255), nullable=False)
    local_path = Column(String(500), nullable=False)
    width = Column(Integer)
    height = Column(Integer)
    file_size = Column(Integer)
    page_number = Column(Integer)
    is_pcb_photo = Column(Boolean, default=None)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    product = relationship("Product", back_populates="photos")
    pdf = relationship("PDF", back_populates="photos")