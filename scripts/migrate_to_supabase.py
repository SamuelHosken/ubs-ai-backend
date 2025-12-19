import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.database import Base
from app.models.document import Document, DocumentChunk
import os
from dotenv import load_dotenv

load_dotenv()

def migrate_data():
    # SQLite (origem)
    sqlite_url = "sqlite:///./ubs_portfolio.db"
    sqlite_engine = create_engine(sqlite_url)
    SQLiteSession = sessionmaker(bind=sqlite_engine)
    sqlite_session = SQLiteSession()

    # Supabase (destino)
    postgres_url = os.getenv("DATABASE_URL")

    if not postgres_url or "postgresql" not in postgres_url:
        print("Erro: DATABASE_URL nao configurada ou nao e PostgreSQL")
        print("Configure o DATABASE_URL no arquivo .env com a URL do Supabase")
        return

    postgres_engine = create_engine(postgres_url)
    PostgresSession = sessionmaker(bind=postgres_engine)
    postgres_session = PostgresSession()

    # Criar tabelas
    print("Criando tabelas no Supabase...")
    Base.metadata.create_all(bind=postgres_engine)

    # Migrar Documents
    print("Migrando documentos...")
    documents = sqlite_session.query(Document).all()

    doc_id_map = {}
    for doc in documents:
        new_doc = Document(
            filename=doc.filename,
            file_type=doc.file_type,
            file_path=doc.file_path,
            title=doc.title,
            upload_date=doc.upload_date,
            portfolio_id=doc.portfolio_id,
            document_category=doc.document_category,
            date_reference=doc.date_reference,
            processed=doc.processed,
            chunk_count=doc.chunk_count,
            extra_metadata=doc.extra_metadata,
            summary=doc.summary
        )
        postgres_session.add(new_doc)
        postgres_session.flush()
        doc_id_map[doc.id] = new_doc.id

    postgres_session.commit()
    print(f"  {len(documents)} documentos migrados")

    # Migrar Chunks
    print("Migrando chunks...")
    chunks = sqlite_session.query(DocumentChunk).all()

    for chunk in chunks:
        new_chunk = DocumentChunk(
            document_id=doc_id_map.get(chunk.document_id),
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            embedding_id=chunk.embedding_id,
            page_number=chunk.page_number,
            chunk_metadata=chunk.chunk_metadata
        )
        postgres_session.add(new_chunk)

    postgres_session.commit()
    print(f"  {len(chunks)} chunks migrados")

    sqlite_session.close()
    postgres_session.close()

    print("\n Migracao completa!")
    print("\n PROXIMOS PASSOS:")
    print("1. Verifique os dados no Supabase Dashboard")
    print("2. Faca backup do arquivo SQLite original")
    print("3. Reinicie a aplicacao")

if __name__ == "__main__":
    print("Migracao SQLite -> Supabase\n")
    confirm = input("Confirma migracao? (sim/nao): ")
    if confirm.lower() == "sim":
        try:
            migrate_data()
        except Exception as e:
            print(f"\n Erro na migracao: {e}")
    else:
        print("Migracao cancelada")
