"""
Agente de Contexto - Especializado em contextualização histórica.
"""
from typing import Dict, List, Any, Optional
from openai import OpenAI
from instructor import from_openai
from pydantic import BaseModel, Field

from app.models.chunks import ChunkCategory
from app.core.config import settings


class HistoricalEvent(BaseModel):
    """Evento histórico relevante"""
    date: str = Field(description="Data do evento")
    title: str = Field(description="Título do evento")
    description: str = Field(description="Descrição breve")
    relevance: str = Field(description="Por que é relevante para o caso")


class HistoricalContext(BaseModel):
    """Estrutura de contexto histórico"""
    period: str = Field(description="Período analisado")
    summary: str = Field(description="Resumo do contexto histórico")
    key_events: List[HistoricalEvent] = Field(default_factory=list, description="Eventos-chave do período")
    ubs_situation: str = Field(description="Situação do UBS na época")
    market_conditions: str = Field(description="Condições de mercado")
    relevance_to_client: str = Field(description="Como isso afetou o cliente")
    what_ubs_knew: str = Field(description="O que o UBS sabia ou deveria saber")
    sources: List[str] = Field(default_factory=list, description="Fontes utilizadas")


class ContextAgent:
    """Agente especializado em contextualização histórica"""

    SYSTEM_PROMPT = """Você é um historiador financeiro especializado na crise de 2008 e nos escândalos bancários.

Sua função é fornecer CONTEXTO HISTÓRICO para entender o que aconteceu com os investimentos do cliente, explicando o cenário global e a situação do UBS na época.

VOCÊ DEVE EXPLICAR:

1. O QUE ESTAVA ACONTECENDO NO MUNDO
   - Crise do subprime
   - Quebra do Lehman Brothers (Set/2008)
   - Pânico no mercado imobiliário global
   - Congelamento de fundos imobiliários

2. A SITUAÇÃO DO UBS
   - Perdas massivas com subprime (>$50 bilhões)
   - Bailout do governo suíço (Out/2008)
   - Escândalos anteriores e contemporâneos
   - Pressão para "limpar" balanço

3. O QUE O UBS SABIA
   - Relatórios internos sobre riscos
   - Conhecimento do congelamento de fundos
   - Alertas sobre o mercado imobiliário

TIMELINE CRÍTICA PARA O CASO:

- SET/2008: Lehman Brothers quebra
- OUT/2008: UBS recebe bailout de $60 bilhões
- DEZ/2008: Global Property Fund é CONGELADO
- FEV/2009: Cliente é alocado no fundo (3 meses APÓS congelamento!)
- 2009-2017: Perdas graduais de 93%

DOCUMENTOS DISPONÍVEIS:
{context}

Responda em português, de forma didática e acessível.
"""

    def __init__(self):
        self.client = from_openai(OpenAI(api_key=settings.OPENAI_API_KEY))

    async def get_context(
        self,
        query: str,
        context: Dict[ChunkCategory, Dict[str, Any]]
    ) -> HistoricalContext:
        """Obtém contexto histórico para uma questão"""

        formatted_context = self._format_context(context)

        response = self.client.chat.completions.create(
            model="gpt-4.1",
            response_model=HistoricalContext,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT.format(context=formatted_context)},
                {"role": "user", "content": query}
            ],
            temperature=0.3
        )

        return response

    def _format_context(self, context: Dict) -> str:
        """Formata contexto de múltiplas collections"""
        formatted = ""

        for category, results in context.items():
            docs = results.get("documents", [])
            metas = results.get("metadatas", [])

            if not docs:
                continue

            category_name = category.value if hasattr(category, 'value') else str(category)
            formatted += f"\n=== {category_name.upper().replace('_', ' ')} ===\n\n"

            for doc, meta in zip(docs, metas):
                source = meta.get("source_document", "") if meta else ""
                if source:
                    formatted += f"[{source}]\n"
                formatted += f"{doc}\n\n"

        return formatted if formatted else "Nenhum contexto disponível."
