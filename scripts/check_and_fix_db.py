"""
Script para verificar e corrigir o schema do banco de dados
"""
import sys
from pathlib import Path

# Adicionar o diretório backend ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text, inspect
from app.models.database import engine

def check_and_fix_db():
    """Verifica e corrige o schema do banco"""

    with engine.connect() as conn:
        # Verificar colunas atuais
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('users')]

        print("Colunas atuais na tabela users:")
        print(columns)

        if 'role' not in columns:
            print("\n❌ Coluna 'role' não encontrada. Adicionando...")
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR NOT NULL DEFAULT 'oficial'"))
                conn.commit()
                print("✅ Coluna 'role' adicionada!")
            except Exception as e:
                print(f"❌ Erro ao adicionar coluna: {e}")
                conn.rollback()
        else:
            print("\n✅ Coluna 'role' já existe!")

if __name__ == "__main__":
    check_and_fix_db()
