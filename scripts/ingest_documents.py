import sys
import os
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.services.document_processor import DocumentProcessor
from app.services.embedding_service import EmbeddingService
from app.models.document import Document, DocumentChunk
from app.models.database import SessionLocal, init_db

def ingest_documents(data_folder: str = "./data/raw"):
    """Processa e ingere todos os documentos"""

    # Criar tabelas
    print("Inicializando banco de dados...")
    init_db()

    db = SessionLocal()
    processor = DocumentProcessor()
    embedding_service = EmbeddingService()

    data_path = Path(data_folder)

    if not data_path.exists():
        print(f"Pasta {data_folder} não existe. Criando...")
        data_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ Pasta criada. Adicione documentos em {data_folder}")
        return

    files = list(data_path.rglob("*"))
    document_files = [f for f in files if f.is_file()]

    if not document_files:
        print(f"⚠️  Nenhum documento encontrado em {data_folder}")
        print("Adicione arquivos PDF ou Excel e execute novamente.")
        return

    print(f"Encontrados {len(document_files)} arquivos\n")

    for file_path in document_files:
        print(f"Processando: {file_path.name}")

        suffix = file_path.suffix.lower()

        try:
            # Verificar se já foi processado
            existing = db.query(Document).filter(Document.filename == file_path.name).first()
            if existing:
                print(f"⚠️  {file_path.name} já foi processado. Pulando...")
                continue

            if suffix == ".pdf":
                chunks = processor.process_pdf(str(file_path))
            elif suffix in [".xlsx", ".xls"]:
                chunks = processor.process_excel(str(file_path))
            elif suffix == ".txt":
                chunks = processor.process_txt(str(file_path))
            else:
                print(f"⚠️  Tipo não suportado: {suffix}")
                continue

            # Criar registro do documento
            doc = Document(
                filename=file_path.name,
                file_type=suffix[1:],
                file_path=str(file_path),
                processed=False
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)

            # Processar chunks
            for idx, chunk in enumerate(chunks):
                chunk_id = f"doc_{doc.id}_chunk_{idx}"

                # Adicionar ao vector DB
                embedding_service.add_document_chunk(
                    chunk_id=chunk_id,
                    text=chunk["content"],
                    metadata={
                        "document_id": doc.id,
                        "filename": doc.filename,
                        "page": chunk.get("page"),
                        "type": chunk.get("type")
                    }
                )

                # Salvar chunk no banco
                db_chunk = DocumentChunk(
                    document_id=doc.id,
                    chunk_index=idx,
                    content=chunk["content"],
                    embedding_id=chunk_id,
                    page_number=chunk.get("page"),
                    chunk_metadata=chunk
                )
                db.add(db_chunk)

            doc.processed = True
            doc.chunk_count = len(chunks)
            db.commit()

            print(f"✓ {file_path.name} - {len(chunks)} chunks processados\n")

        except Exception as e:
            print(f"✗ Erro ao processar {file_path.name}: {str(e)}\n")
            db.rollback()

    db.close()
    print("✓ Ingestão completa!")
    print(f"Total de documentos na collection: {embedding_service.get_collection_count()}")

if __name__ == "__main__":
    ingest_documents()
