"""
Agente Forense - Especializado em análise de má conduta e violações.
"""
from typing import Dict, List, Any, Optional
from openai import OpenAI
from instructor import from_openai
from pydantic import BaseModel, Field
import os

from app.models.chunks import ChunkCategory
from app.core.config import settings


class ViolationAnalysis(BaseModel):
    """Estrutura de análise de violação"""
    violation_found: bool = Field(description="Se uma violação foi identificada")
    violation_type: Optional[str] = Field(default=None, description="Tipo: suitability, disclosure, fiduciary, timing, conflicts")
    description: str = Field(description="Descrição detalhada da violação ou da análise")
    evidence: List[str] = Field(default_factory=list, description="Lista de evidências encontradas")
    ubs_rules_violated: List[str] = Field(default_factory=list, description="Regras do próprio UBS que foram violadas")
    severity: str = Field(default="moderate", description="Severidade: critical, grave, moderate, minor")
    responsibility: str = Field(default="undetermined", description="Atribuição: ubs, client, market, shared")
    financial_impact: Optional[str] = Field(default=None, description="Impacto financeiro estimado")
    recommendation: Optional[str] = Field(default=None, description="Recomendação para o caso")
    sources: List[str] = Field(default_factory=list, description="Fontes documentais utilizadas")


class ForensicAgent:
    """Agente especializado em análise forense de má conduta bancária"""

    SYSTEM_PROMPT = """Você é um analista forense especializado em má conduta bancária e violações de compliance no setor financeiro.

Sua função é analisar evidências e determinar se houve violações por parte do UBS na gestão dos investimentos do cliente.

TIPOS DE VIOLAÇÕES A IDENTIFICAR:

1. SUITABILITY (Adequação)
   - Produto inadequado para o perfil do cliente
   - Cliente conservador ("Yield") em produto de alto risco
   - Falta de diversificação adequada

2. DISCLOSURE (Divulgação)
   - Falta de informação sobre riscos
   - Não informar que o fundo estava congelado
   - Omissão de informações relevantes

3. FIDUCIARY (Dever Fiduciário)
   - Não agir no melhor interesse do cliente
   - Priorizar interesses do banco sobre o cliente
   - Não monitorar adequadamente os investimentos

4. TIMING (Momento)
   - Alocação em momento inadequado
   - Investir em fundo já congelado (Global Property Fund em 2009)
   - Não avisar sobre condições adversas

5. CONFLICTS (Conflito de Interesses)
   - Conflito de interesse não divulgado
   - Produtos proprietários empurrados
   - Taxas cobradas mesmo com fundos travados

REGRAS DE ANÁLISE:

1. Seja OBJETIVO e baseie-se apenas nas evidências fornecidas
2. Cite SEMPRE as fontes específicas (documento, página, data)
3. Compare as ações do UBS com suas PRÓPRIAS REGRAS (Code of Conduct, MiFID)
4. Quantifique o impacto financeiro quando possível
5. Atribua responsabilidade claramente

CONTEXTO DO CASO:
- Cliente com perfil "Yield" (conservador)
- Portfolio 02 alocado 100% no Global Property Fund em FEV/2009
- O fundo foi CONGELADO em DEZ/2008 (3 meses antes da alocação)
- Perda total de ~93% do valor investido

DOCUMENTOS DISPONÍVEIS:
{context}
"""

    def __init__(self):
        self.client = from_openai(OpenAI(api_key=settings.OPENAI_API_KEY))

    async def analyze(
        self,
        query: str,
        context: Dict[ChunkCategory, Dict[str, Any]]
    ) -> ViolationAnalysis:
        """Analisa uma questão forense"""

        # Formatar contexto
        formatted_context = self._format_context(context)

        # Chamar LLM com structured output
        response = self.client.chat.completions.create(
            model="gpt-4.1",
            response_model=ViolationAnalysis,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT.format(context=formatted_context)},
                {"role": "user", "content": query}
            ],
            temperature=0.1
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
            formatted += f"\n{'='*60}\n"
            formatted += f"=== {category_name.upper().replace('_', ' ')} ===\n"
            formatted += f"{'='*60}\n\n"

            for doc, meta in zip(docs, metas):
                source = meta.get("source_document", "Unknown") if meta else "Unknown"
                formatted += f"[Fonte: {source}]\n{doc}\n\n---\n\n"

        return formatted if formatted else "Nenhum contexto disponível."
