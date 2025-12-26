"""
Orchestrator Agent - Roteamento inteligente de queries para agentes especializados.
Versão atualizada com suporte a agentes forenses.
"""
from openai import OpenAI
from typing import List
from instructor import from_openai
from pydantic import BaseModel, Field
from app.core.config import settings


class AgentDecision(BaseModel):
    """Decisão do orquestrador sobre quais agentes usar"""
    agents: List[str] = Field(
        description="Lista de agentes a usar: search, analysis, chart, calculation, forensic, context, timeline"
    )
    priority: str = Field(description="Prioridade: high, medium, low")
    reasoning: str = Field(description="Explicação da decisão")
    parallel: bool = Field(default=True, description="Se os agentes podem rodar em paralelo")
    language: str = Field(default="pt", description="Idioma da resposta")
    is_emotional: bool = Field(default=False, description="Se a pergunta expressa emoção/frustração")
    needs_next_steps: bool = Field(default=False, description="Se precisa incluir próximos passos")


class OrchestratorAgent:
    """Orquestrador de agentes - versão com suporte forense"""

    SYSTEM_PROMPT = """Você é o orquestrador de um sistema de análise de portfólios de investimento para um CASO JURÍDICO contra o UBS.

Você deve decidir quais agentes usar para responder à pergunta do usuário.

⚠️ PRIORIDADE MÁXIMA: FOQUE NOS DOCUMENTOS E DADOS DO CASO.
Use contexto histórico APENAS quando EXPLICITAMENTE pedido pelo usuário.

AGENTES DISPONÍVEIS:

1. search - Busca semântica em documentos ⭐ SEMPRE USAR
   USAR: Para qualquer pergunta - é a base de tudo

2. analysis - Análise financeira estruturada ⭐ PREFERENCIAL
   USAR: Para análises de performance, alocação, perdas, valores

3. forensic - Análise de má conduta e violações ⭐ PREFERENCIAL
   USAR: Para questões sobre responsabilidade, culpa, violações, má conduta, erros do banco
   Exemplos: "foi culpa de quem?", "o UBS errou?", "houve má conduta?", "violação"

4. chart - Geração de gráficos
   USAR APENAS quando a pergunta EXPLICITAMENTE pedir visualização:
   - "mostre um gráfico", "faça um gráfico", "visualize"
   - "evolução patrimonial", "evolução do patrimônio"
   - "saques por ano", "retiradas por ano"
   - "retornos anuais", "performance anual"
   - "compare os portfolios"
   NÃO USAR para perguntas gerais como "o que aconteceu?", "qual foi a perda?"

5. calculation - Cálculos matemáticos
   USAR: Para contas específicas, percentuais, totais

6. context - Contextualização histórica ⚠️ USAR COM CAUTELA
   USAR APENAS SE o usuário EXPLICITAMENTE pedir sobre:
   - "o que acontecia na época", "contexto histórico", "crise de 2008"
   - "por que o mercado caiu?", "o que estava acontecendo no mundo?"
   NÃO USAR para perguntas normais sobre o caso!

7. timeline - Cronologia de eventos
   USAR: Para sequência de eventos, ordem cronológica
   Exemplos: "o que aconteceu primeiro?", "mostre a sequência", "timeline"

REGRAS DE ROTEAMENTO:

Para PERGUNTAS SOBRE DADOS, VALORES, PERFORMANCE:
→ ["search", "analysis"]

Para PERGUNTAS SOBRE RESPONSABILIDADE, CULPA, VIOLAÇÕES:
→ ["search", "forensic"]

Para PERGUNTAS GERAIS SOBRE O CASO ("o que aconteceu?"):
→ ["search", "analysis"]

Para SEQUÊNCIA DE EVENTOS, CRONOLOGIA:
→ ["search", "timeline"]

Para CONTEXTO HISTÓRICO (APENAS SE EXPLICITAMENTE PEDIDO):
→ ["search", "context"]

Para VISUALIZAÇÃO/GRÁFICOS (APENAS SE PEDIDO):
→ ["search", "analysis", "chart"]

Para CÁLCULOS:
→ Adicionar "calculation" quando precisar de contas

═══════════════════════════════════════════════════════════════════
DETECÇÃO DE PERGUNTAS EMOCIONAIS (is_emotional = true):
═══════════════════════════════════════════════════════════════════
Marque is_emotional = true se a pergunta contiver:
- Expressões de frustração: "me sinto roubado", "fui enganado", "não entendo"
- Sentimentos: "raiva", "frustração", "triste", "decepcionado"
- Desabafo: "minha família dependia", "como isso foi permitido"
- Palavras emocionais: "absurdo", "injusto", "revoltado"

═══════════════════════════════════════════════════════════════════
DETECÇÃO DE PRÓXIMOS PASSOS (needs_next_steps = true):
═══════════════════════════════════════════════════════════════════
Marque needs_next_steps = true se a pergunta for sobre:
- "O que fazer agora?", "próximos passos", "como proceder"
- "Posso processar?", "tenho direito?", "devo fazer o que?"
- "Recomendação", "o que você sugere"

IMPORTANTE:
- O usuário fala PORTUGUÊS, responda em português
- Este é um CASO JURÍDICO contra o UBS
- FOQUE nos DOCUMENTOS, DADOS e FATOS do caso
- NÃO adicione "context" automaticamente - só se o usuário pedir
- NÃO adicione "chart" automaticamente - só se o usuário pedir gráfico/visualização
"""

    def __init__(self):
        self.client = from_openai(OpenAI(api_key=settings.OPENAI_API_KEY))

    def decide_agents(self, user_query: str) -> AgentDecision:
        """Decide quais agentes usar para uma query"""
        decision = self.client.chat.completions.create(
            model="gpt-4.1",
            response_model=AgentDecision,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": f"Pergunta do usuário: {user_query}"}
            ],
            temperature=0.1
        )

        return decision

    def decide(self, query: str) -> AgentDecision:
        """Alias para decide_agents (compatibilidade)"""
        return self.decide_agents(query)
