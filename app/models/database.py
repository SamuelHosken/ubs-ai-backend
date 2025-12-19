from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Configuração específica para SQLite
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

# Pool settings para evitar MaxClients no Supabase/PostgreSQL
# Supabase free tier tem limite de ~15 conexões em Session mode
pool_settings = {}
if "postgresql" in settings.DATABASE_URL or "supabase" in settings.DATABASE_URL:
    pool_settings = {
        "pool_size": 2,  # Apenas 2 conexões permanentes (conservador)
        "max_overflow": 3,  # Máximo de 5 conexões total (2+3)
        "pool_pre_ping": True,  # Verifica conexões antes de usar
        "pool_recycle": 300,  # Recicla conexões a cada 5 minutos
        "pool_timeout": 30,  # Timeout de 30s esperando por conexão
    }

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    **pool_settings
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Cria todas as tabelas"""
    Base.metadata.create_all(bind=engine)
