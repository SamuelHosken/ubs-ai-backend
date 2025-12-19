from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, ForeignKey, Enum
from sqlalchemy.sql import func
from .database import Base
import enum

class UserRole(str, enum.Enum):
    DEV = "dev"
    OFICIAL = "oficial"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default=UserRole.OFICIAL.value)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, unique=True, index=True)
    file_type = Column(String)
    file_path = Column(String)
    title = Column(String, nullable=True)
    upload_date = Column(DateTime, server_default=func.now())

    portfolio_id = Column(String, index=True, nullable=True)
    document_category = Column(String, nullable=True)
    date_reference = Column(DateTime, nullable=True)

    processed = Column(Boolean, default=False)
    chunk_count = Column(Integer, default=0)
    extra_metadata = Column(JSON, nullable=True)
    summary = Column(Text, nullable=True)

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    chunk_index = Column(Integer)
    content = Column(Text)
    embedding_id = Column(String)
    page_number = Column(Integer, nullable=True)
    chunk_metadata = Column(JSON, nullable=True)
