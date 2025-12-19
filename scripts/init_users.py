"""
Script para inicializar usuários do sistema
Cria o usuário dev e um usuário oficial de exemplo
"""
import sys
from pathlib import Path

# Adicionar o diretório backend ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from app.models.database import SessionLocal, engine, Base, init_db
from app.models.document import User, UserRole
from app.core.security import get_password_hash

def create_initial_users():
    """Cria os usuários iniciais do sistema"""

    # Criar tabelas se não existirem
    print("Criando tabelas...")
    init_db()

    db = SessionLocal()

    try:
        # Verificar se já existem usuários
        existing_users = db.query(User).count()
        if existing_users > 0:
            print(f"⚠️  Já existem {existing_users} usuário(s) no banco.")
            response = input("Deseja continuar e adicionar novos usuários? (s/n): ")
            if response.lower() != 's':
                print("Operação cancelada.")
                return

        # Criar usuário dev
        dev_email = "dev@ubs.com"
        existing_dev = db.query(User).filter(User.email == dev_email).first()

        if not existing_dev:
            dev_user = User(
                email=dev_email,
                full_name="Developer",
                hashed_password=get_password_hash("dev123"),
                role=UserRole.DEV.value,
                is_active=True,
                is_superuser=True
            )
            db.add(dev_user)
            print(f"✅ Usuário dev criado: {dev_email} / dev123")
        else:
            print(f"ℹ️  Usuário dev já existe: {dev_email}")

        # Criar usuário oficial de exemplo
        oficial_email = "usuario@ubs.com"
        existing_oficial = db.query(User).filter(User.email == oficial_email).first()

        if not existing_oficial:
            oficial_user = User(
                email=oficial_email,
                full_name="Usuário Oficial",
                hashed_password=get_password_hash("oficial123"),
                role=UserRole.OFICIAL.value,
                is_active=True,
                is_superuser=False
            )
            db.add(oficial_user)
            print(f"✅ Usuário oficial criado: {oficial_email} / oficial123")
        else:
            print(f"ℹ️  Usuário oficial já existe: {oficial_email}")

        db.commit()
        print("\n🎉 Usuários inicializados com sucesso!")
        print("\nCredenciais de acesso:")
        print("=" * 50)
        print(f"Dev:     {dev_email} / dev123")
        print(f"Oficial: {oficial_email} / oficial123")
        print("=" * 50)

    except Exception as e:
        print(f"❌ Erro ao criar usuários: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_initial_users()
