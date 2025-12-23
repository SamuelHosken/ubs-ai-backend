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

from app.services.storage_service import storage_service


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


class PortfolioDocument(BaseModel):
    """Schema para documento/portfolio dentro de um ano"""
    name: str
    document_type: str
    image_count: int
    thumbnail_path: str


class PortfolioYear(BaseModel):
    """Schema para ano com seus documentos"""
    year: str
    year_label: str
    document_count: int
    image_count: int
    documents: List[PortfolioDocument]


def _is_image_file(filename: str) -> bool:
    """Verifica se o arquivo e uma imagem"""
    return filename.lower().endswith(('.jpg', '.jpeg', '.png'))


def _extract_page_number(filename: str) -> int:
    """Extrai numero da pagina do nome do arquivo"""
    if '-page-' in filename:
        try:
            page_str = filename.split('-page-')[-1].split('.')[0]
            return int(page_str)
        except (ValueError, IndexError):
            pass
    return 1


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
    Lista todas as imagens de portfolios disponiveis.
    Suporta filtros por ano, tipo de documento e busca por texto.
    """
    images = []

    # Listar anos (pastas raiz)
    year_folders = storage_service.list_directory("")

    for folder_year in sorted(year_folders):
        if folder_year.startswith('.'):
            continue

        if not storage_service.is_directory(folder_year):
            continue

        # Filtro por ano
        if year and folder_year != year:
            continue

        # Listar conteudo do ano
        year_items = storage_service.list_directory(folder_year)

        for item_name in year_items:
            if item_name.startswith('.'):
                continue

            item_path = f"{folder_year}/{item_name}"

            if _is_image_file(item_name):
                # Imagem solta na pasta do ano
                doc_type = _extract_document_type(item_name)
                if document_type and document_type.lower() not in doc_type.lower():
                    continue
                if search and search.lower() not in item_name.lower():
                    continue

                images.append(PortfolioImage(
                    year=folder_year,
                    document_name=folder_year,
                    page_number=_extract_page_number(item_name),
                    filename=item_name,
                    path=item_path
                ))
            elif storage_service.is_directory(item_path):
                # Subpasta com imagens
                doc_name = item_name
                doc_type = _extract_document_type(doc_name)

                if document_type and document_type.lower() not in doc_type.lower():
                    continue

                # Listar imagens na subpasta
                doc_items = storage_service.list_directory(item_path)
                for img_name in doc_items:
                    if not _is_image_file(img_name):
                        continue

                    if search:
                        search_lower = search.lower()
                        if (search_lower not in img_name.lower() and
                            search_lower not in doc_name.lower() and
                            search_lower not in folder_year):
                            continue

                    images.append(PortfolioImage(
                        year=folder_year,
                        document_name=doc_name,
                        page_number=_extract_page_number(img_name),
                        filename=img_name,
                        path=f"{item_path}/{img_name}"
                    ))

    # Ordenar por ano e pagina
    images.sort(key=lambda x: (x.year, x.document_name, x.page_number))

    # Paginacao
    return images[skip:skip + limit]


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


@router.get("/images/structure", response_model=List[PortfolioYear])
def get_portfolio_images_structure(
    current_user: User = Depends(get_current_active_user)
) -> List[PortfolioYear]:
    """
    Retorna a estrutura hierarquica das imagens:
    Anos -> Documentos -> (imagens via outro endpoint)
    """
    years_data = []

    # Listar anos (pastas raiz)
    year_folders = storage_service.list_directory("")

    for year in sorted(year_folders):
        if year.startswith('.'):
            continue

        if not storage_service.is_directory(year):
            continue

        year_num = int(year) if year.isdigit() else 0
        year_label = f"20{year.zfill(2)}" if year_num < 50 else f"19{year.zfill(2)}" if year_num < 100 else year

        documents = []
        total_images = 0

        # Listar conteudo do ano
        year_items = storage_service.list_directory(year)

        for item_name in sorted(year_items):
            if item_name.startswith('.'):
                continue

            item_path = f"{year}/{item_name}"

            if _is_image_file(item_name):
                # Imagem solta na pasta do ano
                total_images += 1
                doc_name = item_name.rsplit('.', 1)[0]  # Remove extensao
                doc_type = _extract_document_type(doc_name)
                documents.append(PortfolioDocument(
                    name=doc_name,
                    document_type=doc_type,
                    image_count=1,
                    thumbnail_path=item_path
                ))
            elif storage_service.is_directory(item_path):
                # Subpasta com imagens
                doc_name = item_name
                doc_type = _extract_document_type(doc_name)

                # Contar imagens na subpasta
                doc_items = storage_service.list_directory(item_path)
                image_files = [f for f in sorted(doc_items) if _is_image_file(f)]

                if image_files:
                    total_images += len(image_files)
                    # Usar primeira imagem como thumbnail
                    thumbnail = f"{item_path}/{image_files[0]}"
                    documents.append(PortfolioDocument(
                        name=doc_name,
                        document_type=doc_type,
                        image_count=len(image_files),
                        thumbnail_path=thumbnail
                    ))

        if documents:
            years_data.append(PortfolioYear(
                year=year,
                year_label=year_label,
                document_count=len(documents),
                image_count=total_images,
                documents=documents
            ))

    return years_data


@router.get("/images/stats", response_model=PortfolioImageStats)
def get_portfolio_images_stats(
    current_user: User = Depends(get_current_active_user)
) -> PortfolioImageStats:
    """Retorna estatisticas das imagens de portfolios"""
    total = 0
    years = set()
    doc_types = set()

    # Listar anos
    year_folders = storage_service.list_directory("")

    for year in year_folders:
        if year.startswith('.'):
            continue

        if not storage_service.is_directory(year):
            continue

        years.add(year)

        # Listar conteudo do ano
        year_items = storage_service.list_directory(year)

        for item_name in year_items:
            if item_name.startswith('.'):
                continue

            item_path = f"{year}/{item_name}"

            if _is_image_file(item_name):
                total += 1
                doc_types.add(_extract_document_type(item_name))
            elif storage_service.is_directory(item_path):
                doc_types.add(_extract_document_type(item_name))
                # Contar imagens na subpasta
                doc_items = storage_service.list_directory(item_path)
                for img_name in doc_items:
                    if _is_image_file(img_name):
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
    Suporta tanto storage local quanto S3/R2.
    """
    from urllib.parse import unquote
    from fastapi.responses import RedirectResponse, Response

    image_path = unquote(image_path)

    # Verificar se arquivo existe
    if not storage_service.file_exists(image_path):
        raise HTTPException(status_code=404, detail="Imagem nao encontrada")

    # Se for S3, redirecionar para URL pre-assinada
    if not storage_service.is_local():
        presigned_url = storage_service.get_file_url(image_path)
        if presigned_url:
            return RedirectResponse(url=presigned_url)
        raise HTTPException(status_code=500, detail="Erro ao gerar URL da imagem")

    # Se for local, servir o arquivo diretamente
    local_path = storage_service.get_local_path(image_path)
    if not local_path:
        raise HTTPException(status_code=404, detail="Imagem nao encontrada")

    # Determinar media type baseado na extensao
    suffix = local_path.suffix.lower()
    media_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
    }
    media_type = media_types.get(suffix, 'image/jpeg')

    return FileResponse(
        path=str(local_path),
        media_type=media_type,
        filename=local_path.name
    )
