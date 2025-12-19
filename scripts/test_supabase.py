import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from app.models.database import SessionLocal
from app.models.document import Document, DocumentChunk

def test_connection():
    try:
        db = SessionLocal()

        # Testar conexao
        doc_count = db.query(Document).count()
        chunk_count = db.query(DocumentChunk).count()

        print(" Conexao com Supabase OK!")
        print(f" Total de documentos: {doc_count}")
        print(f" Total de chunks: {chunk_count}")

        # Listar documentos
        if doc_count > 0:
            docs = db.query(Document).limit(5).all()
            print(f"\nPrimeiros documentos:")
            for doc in docs:
                print(f"  - {doc.filename} ({doc.chunk_count} chunks)")

        db.close()
        return True

    except Exception as e:
        print(f" Erro: {e}")
        return False

if __name__ == "__main__":
    print("Testando conexao com Supabase...\n")
    success = test_connection()

    if success:
        print("\n Tudo funcionando!")
    else:
        print("\n Verifique a configuracao DATABASE_URL no .env")
