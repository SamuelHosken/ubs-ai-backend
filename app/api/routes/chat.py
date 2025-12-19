from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from typing import Optional, List
from app.schemas.chat import ChatRequest, ChatResponse, ConversationResponse, ConversationWithMessages
from app.services.embedding_service import EmbeddingService
from app.services.multi_agent_service import MultiAgentChatService
from app.core.dependencies import get_current_active_user
from app.models import User, Conversation, Message, get_db
from sqlalchemy.sql import func
from sse_starlette.sse import EventSourceResponse
import asyncio
import json
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# Singleton
embedding_service = None
chat_service = None

def get_services():
    global embedding_service, chat_service
    if chat_service is None:
        embedding_service = EmbeddingService()
        chat_service = MultiAgentChatService(embedding_service)
    return chat_service

@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    conversation_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Endpoint com multi-agente (requer autenticacao)"""
    try:
        # Criar ou buscar conversa
        if conversation_id:
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.id
            ).first()
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversa não encontrada")
        else:
            # Nova conversa - usar primeira mensagem como título
            conversation = Conversation(
                user_id=current_user.id,
                title=request.message[:50]
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)

        # Salvar mensagem do usuário
        user_message = Message(
            conversation_id=conversation.id,
            role="user",
            content=request.message
        )
        db.add(user_message)
        db.flush()

        # Processar query
        service = get_services()

        # Adicionar date_range à query se fornecido
        query = request.message
        if request.date_range:
            date_context = f"\n[CONTEXTO: Análise limitada ao período de {request.date_range.start_year} a {request.date_range.end_year}]"
            query = query + date_context

        result = await service.process_query(
            query=query,
            conversation_history=[msg.model_dump() for msg in request.conversation_history]
        )

        # Salvar resposta do assistente
        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=result["response"],
            tokens_used=result.get("tokens_used", 0),
            sources=result.get("sources", []),
            chart_data=result.get("chart"),
            agents_used=result.get("agents_used", [])
        )
        db.add(assistant_message)

        # Atualizar contadores
        conversation.message_count += 2
        conversation.tokens_used += result.get("tokens_used", 0)
        conversation.updated_at = func.now()

        db.commit()

        # Adicionar conversation_id na resposta
        response_data = ChatResponse(**result)
        response_data.conversation_id = conversation.id

        return response_data

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error in chat endpoint: {e}")
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    conversation_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Endpoint SSE que mostra o 'pensamento' da IA em tempo real"""

    async def event_generator():
        try:
            # Criar ou buscar conversa
            if conversation_id:
                conversation = db.query(Conversation).filter(
                    Conversation.id == conversation_id,
                    Conversation.user_id == current_user.id
                ).first()
                if not conversation:
                    yield {"event": "error", "data": json.dumps({"error": "Conversa não encontrada"})}
                    return
            else:
                conversation = Conversation(
                    user_id=current_user.id,
                    title=request.message[:50]
                )
                db.add(conversation)
                db.commit()
                db.refresh(conversation)

            # Salvar mensagem do usuário
            user_message = Message(
                conversation_id=conversation.id,
                role="user",
                content=request.message
            )
            db.add(user_message)
            db.flush()

            service = get_services()

            # Preparar query
            query = request.message
            if request.date_range:
                date_context = f"\n[CONTEXTO: Análise limitada ao período de {request.date_range.start_year} a {request.date_range.end_year}]"
                query = query + date_context

            # Processar com streaming de eventos
            result = None
            async for event in service.process_query_streaming(
                query=query,
                conversation_history=[msg.model_dump() for msg in request.conversation_history]
            ):
                sse_event = {"event": event["type"], "data": json.dumps(event["data"])}
                logger.info(f"[SSE] Sending: {sse_event}")
                yield sse_event

                # Guardar resultado final
                if event["type"] == "complete":
                    result = event["data"]

            # Salvar resposta se tivermos resultado
            if result:
                assistant_message = Message(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=result.get("response", ""),
                    tokens_used=result.get("tokens_used", 0),
                    sources=result.get("sources", []),
                    chart_data=result.get("chart"),
                    agents_used=result.get("agents_used", [])
                )
                db.add(assistant_message)

                conversation.message_count += 2
                conversation.tokens_used += result.get("tokens_used", 0)
                conversation.updated_at = func.now()

                db.commit()

                # Enviar ID da conversa
                yield {"event": "conversation", "data": json.dumps({"id": conversation.id})}

        except Exception as e:
            db.rollback()
            logger.error(f"Error in stream: {e}")
            yield {"event": "error", "data": json.dumps({"error": str(e)})}

    return EventSourceResponse(event_generator())


@router.get("/agents/status")
async def agents_status():
    """Status dos agentes"""
    return {
        "agents": ["orchestrator", "search", "analysis", "chart", "calculation"],
        "status": "operational"
    }

@router.get("/status")
async def chat_status():
    """Status do servico de chat"""
    try:
        service = get_services()
        count = embedding_service.get_collection_count() if embedding_service else 0
        return {
            "status": "operational",
            "documents_indexed": count,
            "multi_agent": True
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20
):
    """Lista conversas do usuário ordenadas por atualização"""
    conversations = db.query(Conversation).filter(
        Conversation.user_id == current_user.id
    ).order_by(
        Conversation.updated_at.desc()
    ).offset(skip).limit(limit).all()

    return conversations

@router.get("/conversations/{conversation_id}/messages", response_model=ConversationWithMessages)
async def get_conversation_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Busca mensagens de uma conversa específica"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at.asc()).all()

    return ConversationWithMessages(
        conversation=conversation,
        messages=messages
    )

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Deleta uma conversa e todas suas mensagens (CASCADE)"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    db.delete(conversation)
    db.commit()

    return {"message": "Conversa deletada com sucesso"}
