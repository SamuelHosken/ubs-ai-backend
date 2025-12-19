"""
Script para adicionar a coluna 'role' à tabela users
"""
import sys
from pathlib import Path

# Adicionar o diretório backend ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from app.models.database import engine

def add_role_column():
    """Adiciona a coluna role à tabela users"""

    with engine.connect() as conn:
        try:
            # Verificar se a coluna já existe
            check_query = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='users' AND column_name='role'
            """)
            result = conn.execute(check_query)

            if result.fetchone():
                print("ℹ️  Coluna 'role' já existe na tabela users")
                return

            # Adicionar a coluna role
            print("Adicionando coluna 'role' à tabela users...")
            alter_query = text("""
                ALTER TABLE users
                ADD COLUMN role VARCHAR NOT NULL DEFAULT 'oficial'
            """)
            conn.execute(alter_query)
            conn.commit()

            print("✅ Coluna 'role' adicionada com sucesso!")
            print("   Todos os usuários existentes foram definidos como 'oficial' por padrão")

        except Exception as e:
            print(f"❌ Erro ao adicionar coluna: {e}")
            conn.rollback()
            raise

if __name__ == "__main__":
    add_role_column()
