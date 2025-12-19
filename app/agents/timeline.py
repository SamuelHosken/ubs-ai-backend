"""
Agente de Timeline - Especializado em criar cronologias de eventos.
"""
from typing import Dict, List, Any, Optional
from openai import OpenAI
from instructor import from_openai
from pydantic import BaseModel, Field

from app.models.chunks import ChunkCategory
from app.core.config import settings


class TimelineEvent(BaseModel):
    """Evento na timeline"""
    date: str = Field(description="Data do evento (YYYY-MM-DD ou YYYY-MM)")
    category: str = Field(description="Categoria: global, ubs, client, fund")
    title: str = Field(description="Título curto do evento")
    description: str = Field(description="Descrição do evento")
    impact: str = Field(description="Impacto no caso")
    source: Optional[str] = Field(default=None, description="Fonte documental")


class Timeline(BaseModel):
    """Timeline completa de eventos"""
    title: str = Field(description="Título da timeline")
    period: str = Field(description="Período coberto")
    summary: str = Field(description="Resumo da narrativa cronológica")
    events: List[TimelineEvent] = Field(default_factory=list, description="Lista de eventos em ordem cronológica")
    key_insight: str = Field(description="Principal insight da análise cronológica")
    pattern_detected: Optional[str] = Field(default=None, description="Padrão identificado nos eventos")


class TimelineAgent:
    """Agente especializado em criar timelines cronológicas"""

    SYSTEM_PROMPT = """Você é um especialista em criar narrativas cronológicas para casos jurídicos.

Sua função é organizar eventos em uma TIMELINE CLARA que demonstre a sequência de acontecimentos relevantes para o caso contra o UBS.

FORMATO DA TIMELINE:

Para cada evento, inclua:
- DATA precisa (quando possível)
- CATEGORIA (global, ubs, client, fund)
- TÍTULO curto
- DESCRIÇÃO do que aconteceu
- IMPACTO no caso do cliente

EVENTOS CRÍTICOS A DESTACAR:

1. ANTES DA ALOCAÇÃO (contexto)
   - Escândalos anteriores do UBS
   - Crise do subprime se desenvolvendo
   - Alertas sobre mercado imobiliário

2. O MOMENTO CRÍTICO (Set-Dez 2008)
   - Quebra do Lehman (15/09/2008)
   - Bailout do UBS (16/10/2008)
   - Congelamento do Global Property Fund (Dez/2008)

3. A ALOCAÇÃO PROBLEMÁTICA (Fev 2009)
   - Cliente alocado no fundo JÁ CONGELADO
   - Sem possibilidade de resgate
   - UBS sabia da situação

4. AS PERDAS (2009-2017)
   - Desvalorização gradual
   - Taxas continuaram sendo cobradas
   - Cliente preso no investimento

DOCUMENTOS DISPONÍVEIS:
{context}

Crie uma timeline CRONOLÓGICA, clara e bem documentada.
Responda em português.
"""

    def __init__(self):
        self.client = from_openai(OpenAI(api_key=settings.OPENAI_API_KEY))

    async def create_timeline(
        self,
        query: str,
        context: Dict[ChunkCategory, Dict[str, Any]]
    ) -> Timeline:
        """Cria uma timeline de eventos"""

        formatted_context = self._format_context(context)

        response = self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            response_model=Timeline,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT.format(context=formatted_context)},
                {"role": "user", "content": query}
            ],
            temperature=0.2
        )

        return response

    def _format_context(self, context: Dict) -> str:
        """Formata contexto de múltiplas collections"""
        formatted = ""

        # Priorizar timeline do cliente e contexto histórico
        priority_order = [
            ChunkCategory.CLIENT,
            ChunkCategory.CONTEXT,
            ChunkCategory.FACTS,
            ChunkCategory.FORENSIC,
            ChunkCategory.UBS_OFFICIAL
        ]

        for category in priority_order:
            if category not in context:
                continue

            results = context[category]
            docs = results.get("documents", [])
            metas = results.get("metadatas", [])

            if not docs:
                continue

            category_name = category.value if hasattr(category, 'value') else str(category)
            formatted += f"\n=== {category_name.upper().replace('_', ' ')} ===\n\n"

            for doc, meta in zip(docs, metas):
                formatted += f"{doc}\n\n"

        return formatted if formatted else "Nenhum contexto disponível."
