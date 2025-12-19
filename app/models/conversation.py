from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from .database import Base
from app.core.config import settings

# Usa JSONB se PostgreSQL, JSON se SQLite
JSON_TYPE = JSONB if "postgresql" in settings.DATABASE_URL else JSON

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    message_count = Column(Integer, default=0)
    tokens_used = Column(Integer, default=0)

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    tokens_used = Column(Integer, nullable=True)
    sources = Column(JSON_TYPE, nullable=True)
    chart_data = Column(JSON_TYPE, nullable=True)
    agents_used = Column(JSON_TYPE, nullable=True)
