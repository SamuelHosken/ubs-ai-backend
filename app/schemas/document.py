from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any

class DocumentBase(BaseModel):
    filename: str
    file_type: Optional[str] = None
    title: Optional[str] = None
    portfolio_id: Optional[str] = None
    document_category: Optional[str] = None

class DocumentCreate(DocumentBase):
    file_path: str

class DocumentResponse(DocumentBase):
    id: int
    file_path: str
    upload_date: datetime
    processed: bool
    chunk_count: int
    extra_metadata: Optional[Dict[str, Any]] = None
    summary: Optional[str] = None
    date_reference: Optional[datetime] = None

    class Config:
        from_attributes = True

class DocumentStats(BaseModel):
    total_documents: int
    processed_documents: int
    total_chunks: int
    file_types: Dict[str, int]
