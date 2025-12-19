from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from app.models import get_db, User, Document
from app.schemas.document import DocumentResponse, DocumentStats
from app.core.dependencies import get_current_active_user

router = APIRouter(prefix="/documents", tags=["documents"])

@router.get("/", response_model=List[DocumentResponse])
def list_documents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Listar todos os documentos"""
    documents = db.query(Document).offset(skip).limit(limit).all()
    return documents

@router.get("/stats", response_model=DocumentStats)
def get_document_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Obter estatísticas dos documentos"""
    total_documents = db.query(func.count(Document.id)).scalar()
    processed_documents = db.query(func.count(Document.id)).filter(Document.processed == True).scalar()
    total_chunks = db.query(func.sum(Document.chunk_count)).scalar() or 0

    # Contar por tipo de arquivo
    file_types_query = db.query(
        Document.file_type,
        func.count(Document.id)
    ).group_by(Document.file_type).all()

    file_types = {ft: count for ft, count in file_types_query if ft}

    return {
        "total_documents": total_documents,
        "processed_documents": processed_documents,
        "total_chunks": int(total_chunks),
        "file_types": file_types
    }

@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Obter detalhes de um documento específico"""
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    return document
