from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict
from app.models import get_db, User, Document
from app.schemas.document import DocumentResponse, DocumentStats
from app.core.dependencies import get_current_active_user, get_current_dev_user
from app.services.embedding_service import EmbeddingService
import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)
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


# ============================================================
# ENDPOINTS DE ADMIN (apenas para usuários dev)
# ============================================================

@router.get("/admin/embeddings/status")
def get_embeddings_status(
    current_user: User = Depends(get_current_dev_user)
) -> Dict:
    """Retorna o status de todas as collections de embeddings"""
    try:
        embedding_service = EmbeddingService()
        stats = embedding_service.get_all_collection_stats()

        return {
            "status": "ok",
            "collections": stats,
            "total_embeddings": sum(stats.values())
        }
    except Exception as e:
        logger.error(f"Erro ao obter status dos embeddings: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


def run_ingest_script(script_name: str):
    """Executa um script de ingestão"""
    script_path = Path(__file__).parent.parent.parent.parent / "scripts" / script_name
    logger.info(f"Executando script: {script_path}")

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=600  # 10 minutos timeout
        )

        if result.returncode == 0:
            logger.info(f"Script {script_name} executado com sucesso")
            return {"success": True, "output": result.stdout}
        else:
            logger.error(f"Script {script_name} falhou: {result.stderr}")
            return {"success": False, "error": result.stderr}
    except subprocess.TimeoutExpired:
        logger.error(f"Script {script_name} excedeu o timeout")
        return {"success": False, "error": "Timeout - script demorou mais de 10 minutos"}
    except Exception as e:
        logger.error(f"Erro ao executar script {script_name}: {e}")
        return {"success": False, "error": str(e)}


@router.post("/admin/embeddings/reindex")
async def reindex_embeddings(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_dev_user)
) -> Dict:
    """
    Re-indexa todos os documentos no ChromaDB.
    Executa os scripts de ingestão em background.

    ATENÇÃO: Este processo pode demorar vários minutos e consumir créditos da OpenAI.
    """
    logger.info(f"Iniciando re-indexação por {current_user.email}")

    # Verificar se os scripts existem
    scripts_dir = Path(__file__).parent.parent.parent.parent / "scripts"
    scripts = [
        "ingest_complete_portfolios.py",
        "ingest_forensic.py",
    ]

    missing_scripts = []
    for script in scripts:
        if not (scripts_dir / script).exists():
            missing_scripts.append(script)

    if missing_scripts:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scripts não encontrados: {missing_scripts}"
        )

    # Executar scripts em background
    def run_all_scripts():
        results = {}
        for script in scripts:
            logger.info(f"Executando {script}...")
            results[script] = run_ingest_script(script)
        logger.info(f"Re-indexação completa: {results}")

    background_tasks.add_task(run_all_scripts)

    return {
        "status": "started",
        "message": "Re-indexação iniciada em background. Verifique os logs para acompanhar o progresso.",
        "scripts": scripts
    }
