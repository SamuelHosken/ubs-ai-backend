from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Optional
from app.models import get_db, User, Document
from app.schemas.document import DocumentResponse, DocumentStats
from app.core.dependencies import get_current_active_user, get_current_dev_user
from app.services.embedding_service import EmbeddingService
import logging
import subprocess
import sys
import os
from pathlib import Path
from pydantic import BaseModel

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


# ============================================================
# ENDPOINTS DE IMAGENS DE PORTFOLIOS
# ============================================================

# Caminho base das imagens de portfolios
PORTFOLIOS_IMAGES_PATH = Path(__file__).parent.parent.parent.parent.parent / "portfolios_corrigidos"


class PortfolioImage(BaseModel):
    """Schema para imagem de portfolio"""
    year: str
    document_name: str
    page_number: int
    filename: str
    path: str


class PortfolioImageStats(BaseModel):
    """Estatísticas das imagens"""
    total_images: int
    years: List[str]
    document_types: List[str]


@router.get("/images/list", response_model=List[PortfolioImage])
def list_portfolio_images(
    year: Optional[str] = None,
    document_type: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user)
) -> List[PortfolioImage]:
    """
    Lista todas as imagens de portfolios disponíveis.
    Suporta filtros por ano, tipo de documento e busca por texto.
    """
    if not PORTFOLIOS_IMAGES_PATH.exists():
        logger.warning(f"Pasta de imagens não encontrada: {PORTFOLIOS_IMAGES_PATH}")
        return []

    images = []

    # Percorrer estrutura de pastas
    for year_folder in sorted(PORTFOLIOS_IMAGES_PATH.iterdir()):
        if not year_folder.is_dir() or year_folder.name.startswith('.'):
            continue

        folder_year = year_folder.name

        # Filtro por ano
        if year and folder_year != year:
            continue

        # Procurar imagens diretamente na pasta do ano
        for item in year_folder.iterdir():
            if item.is_file() and item.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                _add_image_to_list(images, item, folder_year, year_folder.name, document_type, search)
            elif item.is_dir():
                # Subpasta com imagens (ex: 13.03.31-Statement of assets...)
                doc_folder_name = item.name
                for img_file in item.iterdir():
                    if img_file.is_file() and img_file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                        _add_image_to_list(images, img_file, folder_year, doc_folder_name, document_type, search)

    # Ordenar por ano e página
    images.sort(key=lambda x: (x.year, x.document_name, x.page_number))

    # Paginação
    return images[skip:skip + limit]


def _add_image_to_list(
    images: List[PortfolioImage],
    img_file: Path,
    year: str,
    doc_name: str,
    document_type: Optional[str],
    search: Optional[str]
):
    """Adiciona imagem à lista se passar nos filtros"""
    filename = img_file.name

    # Extrair número da página do nome do arquivo
    page_num = 1
    if '-page-' in filename:
        try:
            page_str = filename.split('-page-')[-1].split('.')[0]
            page_num = int(page_str)
        except (ValueError, IndexError):
            pass

    # Extrair tipo de documento
    doc_type = _extract_document_type(doc_name)

    # Filtro por tipo de documento
    if document_type and document_type.lower() not in doc_type.lower():
        return

    # Filtro por busca de texto
    if search:
        search_lower = search.lower()
        if (search_lower not in filename.lower() and
            search_lower not in doc_name.lower() and
            search_lower not in year):
            return

    images.append(PortfolioImage(
        year=year,
        document_name=doc_name,
        page_number=page_num,
        filename=filename,
        path=str(img_file.relative_to(PORTFOLIOS_IMAGES_PATH))
    ))


def _extract_document_type(doc_name: str) -> str:
    """Extrai o tipo de documento do nome da pasta/arquivo"""
    doc_name_lower = doc_name.lower()
    if 'statement' in doc_name_lower:
        return 'Statement'
    elif 'agreement' in doc_name_lower:
        return 'Agreement'
    elif 'report' in doc_name_lower:
        return 'Report'
    elif 'fee' in doc_name_lower:
        return 'Fee'
    else:
        return 'Other'


@router.get("/images/stats", response_model=PortfolioImageStats)
def get_portfolio_images_stats(
    current_user: User = Depends(get_current_active_user)
) -> PortfolioImageStats:
    """Retorna estatísticas das imagens de portfolios"""
    if not PORTFOLIOS_IMAGES_PATH.exists():
        return PortfolioImageStats(total_images=0, years=[], document_types=[])

    total = 0
    years = set()
    doc_types = set()

    for year_folder in PORTFOLIOS_IMAGES_PATH.iterdir():
        if not year_folder.is_dir() or year_folder.name.startswith('.'):
            continue

        years.add(year_folder.name)

        for item in year_folder.iterdir():
            if item.is_file() and item.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                total += 1
                doc_types.add(_extract_document_type(item.name))
            elif item.is_dir():
                doc_types.add(_extract_document_type(item.name))
                for img_file in item.iterdir():
                    if img_file.is_file() and img_file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                        total += 1

    return PortfolioImageStats(
        total_images=total,
        years=sorted(list(years)),
        document_types=sorted(list(doc_types))
    )


@router.get("/images/file/{image_path:path}")
def get_portfolio_image(image_path: str):
    """
    Retorna o arquivo de imagem.
    Nota: Esta rota não requer autenticação para permitir uso em tags <img>.
    A segurança é garantida pela validação do caminho.
    """
    # Decodificar o caminho (pode vir URL encoded)
    from urllib.parse import unquote
    image_path = unquote(image_path)

    full_path = PORTFOLIOS_IMAGES_PATH / image_path

    # Segurança: verificar se o caminho está dentro da pasta permitida
    try:
        full_path.resolve().relative_to(PORTFOLIOS_IMAGES_PATH.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Acesso negado")

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Imagem não encontrada")

    # Determinar media type baseado na extensão
    suffix = full_path.suffix.lower()
    media_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
    }
    media_type = media_types.get(suffix, 'image/jpeg')

    return FileResponse(
        path=str(full_path),
        media_type=media_type,
        filename=full_path.name
    )
