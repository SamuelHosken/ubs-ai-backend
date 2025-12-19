"""
Multi-Agent Chat Service - Orquestra múltiplos agentes para responder queries.

HIERARQUIA DE CONHECIMENTO:
1. COMPLETE_ANALYSIS - Fonte principal (narrativa + raciocínio completo)
2. FACTS, FORENSIC - Fontes secundárias (dados específicos)
3. CONTEXT, CLIENT, UBS_OFFICIAL - Fontes terciárias (quando solicitado)

Versão atualizada com suporte a agentes forenses e busca hierárquica.
"""
from app.agents import (
    OrchestratorAgent,
    SearchAgent,
    AnalysisAgent,
    ChartAgent,
    CalculationAgent,
    ForensicAgent,
    ContextAgent,
    TimelineAgent
)
from app.services.embedding_service import EmbeddingService
from app.services.knowledge_base import KnowledgeBase
from app.models.chunks import ChunkCategory
from typing import List, Dict, Any, AsyncGenerator
from openai import OpenAI
from app.core.config import settings


class MultiAgentChatService:
    """Serviço de chat multi-agente com suporte forense"""

    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

        # Inicializar todos os agentes
        self.agents = {
            "orchestrator": OrchestratorAgent(),
            "search": SearchAgent(embedding_service),
            "analysis": AnalysisAgent(),
            "chart": ChartAgent(),
            "calculation": CalculationAgent(),
            "forensic": ForensicAgent(),
            "context": ContextAgent(),
            "timeline": TimelineAgent()
        }

    def _format_conversation_history(self, history: List[Dict]) -> str:
        """Formata o histórico da conversa para incluir no contexto"""
        if not history:
            return ""

        formatted = "\n--- HISTÓRICO DA CONVERSA ---\n"
        for msg in history[-6:]:  # Últimas 6 mensagens (3 trocas)
            role = "Usuário" if msg.get("role") == "user" else "Assistente"
            content = msg.get("content", "")[:500]  # Limitar tamanho
            formatted += f"{role}: {content}\n\n"
        formatted += "--- FIM DO HISTÓRICO ---\n\n"
        return formatted

    async def process_query(
        self,
        query: str,
        conversation_history: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Processa uma query usando o sistema multi-agente.

        HIERARQUIA DE BUSCA:
        1. SEMPRE busca primeiro em COMPLETE_ANALYSIS (fonte principal)
        2. Complementa com FACTS e FORENSIC se necessário
        3. Adiciona CONTEXT, CLIENT, UBS_OFFICIAL apenas quando solicitado
        """
        # Formatar histórico da conversa
        history_context = self._format_conversation_history(conversation_history)

        # 1. Orchestrator decide estratégia (com contexto da conversa)
        full_query = f"{history_context}PERGUNTA ATUAL: {query}" if history_context else query
        decision = self.agents["orchestrator"].decide_agents(full_query)
        agents_to_use = decision.agents

        # 2. Determinar se precisa de fontes terciárias
        include_tertiary = "context" in agents_to_use or "timeline" in agents_to_use

        # 3. BUSCA HIERÁRQUICA - Prioriza COMPLETE_ANALYSIS
        search_results = await self.agents["search"].search_hierarchical(
            query=query,
            n_primary=10,  # Mais resultados da fonte principal
            n_secondary=5,  # Menos das secundárias
            include_tertiary=include_tertiary,
            use_rerank=True
        )

        # 4. Formatar fontes para o resultado
        formatted_sources = self._extract_sources(search_results)

        # 5. Preparar resultado base
        result = {
            "response": "",
            "sources": formatted_sources,
            "agents_used": agents_to_use,
            "tokens_used": 0,
            "reasoning": decision.reasoning
        }

        # 6. Executar agentes especializados
        responses = []

        # Agente Forense
        if "forensic" in agents_to_use:
            try:
                forensic_result = await self.agents["forensic"].analyze(
                    query=query,
                    context=search_results
                )
                responses.append({
                    "agent": "forensic",
                    "content": self._format_forensic_response(forensic_result)
                })
                result["forensic_analysis"] = forensic_result.model_dump()
            except Exception as e:
                print(f"Erro no agente forense: {e}")

        # Agente de Contexto
        if "context" in agents_to_use:
            try:
                context_result = await self.agents["context"].get_context(
                    query=query,
                    context=search_results
                )
                responses.append({
                    "agent": "context",
                    "content": self._format_context_response(context_result)
                })
                result["historical_context"] = context_result.model_dump()
            except Exception as e:
                print(f"Erro no agente de contexto: {e}")

        # Agente de Timeline
        if "timeline" in agents_to_use:
            try:
                timeline_result = await self.agents["timeline"].create_timeline(
                    query=query,
                    context=search_results
                )
                responses.append({
                    "agent": "timeline",
                    "content": self._format_timeline_response(timeline_result)
                })
                result["timeline"] = timeline_result.model_dump()
            except Exception as e:
                print(f"Erro no agente de timeline: {e}")

        # Agente de Análise Financeira
        if "analysis" in agents_to_use:
            try:
                context_text = self.agents["search"].format_context_for_llm(search_results)
                analysis_result = await self.agents["analysis"].analyze(context_text, query)
                responses.append({
                    "agent": "analysis",
                    "content": self._format_analysis_response(analysis_result)
                })
                result["analysis"] = analysis_result.model_dump()
            except Exception as e:
                print(f"Erro no agente de análise: {e}")

        # Agente de Gráficos
        if "chart" in agents_to_use:
            try:
                context_text = self.agents["search"].format_context_for_llm(search_results)
                chart_result = await self.agents["chart"].generate_chart(context_text, query)
                result["chart"] = {
                    "type": chart_result.type,
                    "title": chart_result.title,
                    "data": {
                        "labels": chart_result.data.labels,
                        "datasets": [{
                            "label": chart_result.y_label,
                            "data": chart_result.data.values
                        }]
                    }
                }
            except Exception as e:
                print(f"Erro no agente de gráficos: {e}")

        # 7. Consolidar resposta final (com histórico da conversa)
        if responses:
            result["response"] = self._consolidate_responses(query, responses, history_context)
        else:
            # Resposta padrão com busca simples
            context_text = self.agents["search"].format_context_for_llm(search_results)
            result["response"] = await self._generate_simple_response(query, context_text, history_context)

        return result

    async def process_query_streaming(
        self,
        query: str,
        conversation_history: List[Dict] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Processa uma query usando o sistema multi-agente COM STREAMING de eventos.
        Yield eventos de progresso para mostrar o 'pensamento' da IA.

        HIERARQUIA DE BUSCA:
        1. SEMPRE busca primeiro em COMPLETE_ANALYSIS (fonte principal)
        2. Complementa com FACTS e FORENSIC se necessário
        """
        # Formatar histórico da conversa
        history_context = self._format_conversation_history(conversation_history)

        # 1. Orquestrador decide estratégia
        yield {"type": "thinking", "data": {"step": "orchestrator", "message": "Analisando sua pergunta..."}}

        full_query = f"{history_context}PERGUNTA ATUAL: {query}" if history_context else query
        decision = self.agents["orchestrator"].decide_agents(full_query)
        agents_to_use = decision.agents

        yield {
            "type": "agents",
            "data": {
                "agents": agents_to_use,
                "reasoning": decision.reasoning
            }
        }

        # 2. Determinar se precisa de fontes terciárias
        include_tertiary = "context" in agents_to_use or "timeline" in agents_to_use

        # 3. BUSCA HIERÁRQUICA - Prioriza COMPLETE_ANALYSIS
        yield {"type": "thinking", "data": {"step": "search", "message": "Consultando base de conhecimento principal..."}}

        search_results = await self.agents["search"].search_hierarchical(
            query=query,
            n_primary=10,
            n_secondary=5,
            include_tertiary=include_tertiary,
            use_rerank=True
        )

        # Contar documentos encontrados
        total_docs = sum(len(r.get("documents", [])) for r in search_results.values())
        yield {
            "type": "thinking",
            "data": {"step": "search_done", "message": f"Encontrados {total_docs} documentos relevantes"}
        }

        # 4. Formatar fontes
        formatted_sources = self._extract_sources(search_results)

        # 5. Preparar resultado base
        result = {
            "response": "",
            "sources": formatted_sources,
            "agents_used": agents_to_use,
            "tokens_used": 0,
            "reasoning": decision.reasoning
        }

        # 6. Executar agentes especializados
        responses = []

        # Agente Forense
        if "forensic" in agents_to_use:
            yield {"type": "thinking", "data": {"step": "forensic", "message": "Agente Forense analisando violações..."}}
            try:
                forensic_result = await self.agents["forensic"].analyze(
                    query=query,
                    context=search_results
                )
                responses.append({
                    "agent": "forensic",
                    "content": self._format_forensic_response(forensic_result)
                })
                result["forensic_analysis"] = forensic_result.model_dump()
            except Exception as e:
                print(f"Erro no agente forense: {e}")

        # Agente de Contexto
        if "context" in agents_to_use:
            yield {"type": "thinking", "data": {"step": "context", "message": "Agente de Contexto analisando período histórico..."}}
            try:
                context_result = await self.agents["context"].get_context(
                    query=query,
                    context=search_results
                )
                responses.append({
                    "agent": "context",
                    "content": self._format_context_response(context_result)
                })
                result["historical_context"] = context_result.model_dump()
            except Exception as e:
                print(f"Erro no agente de contexto: {e}")

        # Agente de Timeline
        if "timeline" in agents_to_use:
            yield {"type": "thinking", "data": {"step": "timeline", "message": "Agente de Timeline montando cronologia..."}}
            try:
                timeline_result = await self.agents["timeline"].create_timeline(
                    query=query,
                    context=search_results
                )
                responses.append({
                    "agent": "timeline",
                    "content": self._format_timeline_response(timeline_result)
                })
                result["timeline"] = timeline_result.model_dump()
            except Exception as e:
                print(f"Erro no agente de timeline: {e}")

        # Agente de Análise Financeira
        if "analysis" in agents_to_use:
            yield {"type": "thinking", "data": {"step": "analysis", "message": "Agente de Análise processando dados financeiros..."}}
            try:
                context_text = self.agents["search"].format_context_for_llm(search_results)
                analysis_result = await self.agents["analysis"].analyze(context_text, query)
                responses.append({
                    "agent": "analysis",
                    "content": self._format_analysis_response(analysis_result)
                })
                result["analysis"] = analysis_result.model_dump()
            except Exception as e:
                print(f"Erro no agente de análise: {e}")

        # Agente de Gráficos
        if "chart" in agents_to_use:
            yield {"type": "thinking", "data": {"step": "chart", "message": "Agente de Gráficos gerando visualização..."}}
            try:
                context_text = self.agents["search"].format_context_for_llm(search_results)
                chart_result = await self.agents["chart"].generate_chart(context_text, query)
                result["chart"] = {
                    "type": chart_result.type,
                    "title": chart_result.title,
                    "data": {
                        "labels": chart_result.data.labels,
                        "datasets": [{
                            "label": chart_result.y_label,
                            "data": chart_result.data.values
                        }]
                    }
                }
            except Exception as e:
                print(f"Erro no agente de gráficos: {e}")

        # 7. Consolidar resposta final
        yield {"type": "thinking", "data": {"step": "consolidate", "message": "Consolidando resposta final..."}}

        if responses:
            result["response"] = self._consolidate_responses(query, responses, history_context)
        else:
            context_text = self.agents["search"].format_context_for_llm(search_results)
            result["response"] = await self._generate_simple_response(query, context_text, history_context)

        # Enviar resultado completo
        yield {"type": "complete", "data": result}

    def _get_categories_for_agents(self, agents: List[str]) -> List[ChunkCategory]:
        """
        Determina quais collections buscar baseado nos agentes.

        HIERARQUIA:
        - COMPLETE_ANALYSIS: SEMPRE incluir (fonte principal)
        - FACTS, FORENSIC: Incluir por padrão (dados específicos)
        - CONTEXT, CLIENT, UBS_OFFICIAL: Apenas quando solicitado
        """
        categories = set()

        # SEMPRE incluir COMPLETE_ANALYSIS como fonte principal
        categories.add(ChunkCategory.COMPLETE_ANALYSIS)

        # Fontes secundárias por padrão
        categories.add(ChunkCategory.FACTS)
        categories.add(ChunkCategory.FORENSIC)

        # Fontes terciárias apenas quando solicitado
        if "context" in agents:
            categories.add(ChunkCategory.CONTEXT)

        if "timeline" in agents:
            categories.add(ChunkCategory.CLIENT)

        return list(categories)

    def _extract_sources(self, search_results: Dict[ChunkCategory, Dict]) -> List[Dict]:
        """Extrai e formata fontes de todas as collections"""
        sources = []
        seen = set()

        for category, results in search_results.items():
            metas = results.get("metadatas", [])
            for meta in metas:
                if not meta:
                    continue

                source_doc = meta.get("source_document", "")
                if source_doc and source_doc not in seen:
                    seen.add(source_doc)
                    sources.append({
                        "filename": source_doc,
                        "page": meta.get("source_page"),
                        "document_type": category.value,
                        "relevance": meta.get("relevance", "high")
                    })

        return sources[:10]  # Limitar a 10 fontes

    def _format_forensic_response(self, result) -> str:
        """Formata resposta do agente forense"""
        response = ""

        if result.violation_found:
            response += f"**Violação Identificada: {result.violation_type}**\n\n"
            response += f"{result.description}\n\n"

            if result.evidence:
                response += "**Evidências:**\n"
                for ev in result.evidence:
                    response += f"- {ev}\n"
                response += "\n"

            if result.ubs_rules_violated:
                response += "**Regras do UBS Violadas:**\n"
                for rule in result.ubs_rules_violated:
                    response += f"- {rule}\n"
                response += "\n"

            response += f"**Severidade:** {result.severity}\n"
            response += f"**Responsabilidade:** {result.responsibility}\n"

            if result.financial_impact:
                response += f"**Impacto Financeiro:** {result.financial_impact}\n"

            if result.recommendation:
                response += f"\n**Recomendação:** {result.recommendation}\n"
        else:
            response = result.description

        return response

    def _format_context_response(self, result) -> str:
        """Formata resposta do agente de contexto"""
        response = f"**Período: {result.period}**\n\n"
        response += f"{result.summary}\n\n"

        if result.key_events:
            response += "**Eventos-Chave:**\n"
            for event in result.key_events:
                response += f"- **{event.date}**: {event.title}\n"
                response += f"  {event.description}\n"
                response += f"  *Relevância: {event.relevance}*\n\n"

        response += f"**Situação do UBS:** {result.ubs_situation}\n\n"
        response += f"**Condições de Mercado:** {result.market_conditions}\n\n"
        response += f"**O que o UBS Sabia:** {result.what_ubs_knew}\n\n"
        response += f"**Impacto no Cliente:** {result.relevance_to_client}\n"

        return response

    def _format_timeline_response(self, result) -> str:
        """Formata resposta do agente de timeline"""
        response = f"**{result.title}**\n"
        response += f"*Período: {result.period}*\n\n"
        response += f"{result.summary}\n\n"

        if result.events:
            response += "**Cronologia de Eventos:**\n\n"
            for event in result.events:
                category_emoji = {
                    "global": "🌍",
                    "ubs": "🏦",
                    "client": "👤",
                    "fund": "📊"
                }.get(event.category, "📌")

                response += f"{category_emoji} **{event.date}** - {event.title}\n"
                response += f"   {event.description}\n"
                response += f"   *Impacto: {event.impact}*\n\n"

        response += f"\n**Insight Principal:** {result.key_insight}\n"

        if result.pattern_detected:
            response += f"\n**Padrão Identificado:** {result.pattern_detected}\n"

        return response

    def _format_analysis_response(self, result) -> str:
        """Formata resposta do agente de análise"""
        response = f"{result.summary}\n\n"

        if result.key_findings:
            response += "**Principais Descobertas:**\n"
            for finding in result.key_findings:
                response += f"- {finding}\n"
            response += "\n"

        if result.total_amount:
            response += f"**Valor Total:** EUR {result.total_amount:,.2f}\n"

        if result.recommendation:
            response += f"\n**Recomendação:** {result.recommendation}\n"

        return response

    def _consolidate_responses(self, query: str, responses: List[Dict], history_context: str = "") -> str:
        """Consolida respostas de múltiplos agentes em uma resposta coerente"""
        # Montar contexto com todas as respostas
        context_parts = []
        for resp in responses:
            context_parts.append(f"[{resp['agent'].upper()}]\n{resp['content']}")

        combined_context = "\n\n---\n\n".join(context_parts)

        # Incluir histórico da conversa se existir
        history_section = ""
        if history_context:
            history_section = f"""
{history_context}
IMPORTANTE: Use o histórico acima para entender o contexto da conversa. Se o usuário se referir a algo mencionado antes, use essa informação.

"""

        # Obter contexto fixo da Knowledge Base
        fixed_knowledge = KnowledgeBase.get_fixed_context()

        # Usar GPT para consolidar
        consolidation_prompt = f"""Você é um assistente especializado em análise de casos jurídicos contra bancos.
{history_section}
O usuário perguntou: "{query}"

══════════════════════════════════════════════════════════════════════════════
DADOS OFICIAIS DOS PORTFOLIOS (USE ESTES DADOS - SÃO A FONTE PRINCIPAL):
══════════════════════════════════════════════════════════════════════════════
{fixed_knowledge}

══════════════════════════════════════════════════════════════════════════════
ANÁLISE DOS AGENTES:
══════════════════════════════════════════════════════════════════════════════
{combined_context}

INSTRUÇÕES CRÍTICAS:
1. USE os dados das TABELAS OFICIAIS acima
2. Para perguntas sobre retiradas/saques: consulte "LISTA DE SAQUES POR ANO"
3. NUNCA diga "não tem dados" - os dados estão nas tabelas acima

FORMATO DA RESPOSTA (IMPORTANTE):
- Use **negrito** para destacar números e informações importantes
- Divida em parágrafos curtos (2-3 linhas cada)
- Use listas com bullet points para dados
- NÃO mostre dados técnicos (type:, xAxis:, data:, etc.)
- Seja conciso mas bem formatado

EXEMPLO DE FORMATAÇÃO IDEAL:
"Aqui está o gráfico com todas as **retiradas do Portfolio 01** entre **2000 e 2016**.

**Destaques principais:**
- **Total sacado:** EUR 1.133.600
- **Maior saque:** 2016 com EUR 140.700
- **Primeiro grande saque:** 2000 com EUR 256.400

O gráfico evidencia que **95% da redução patrimonial** foi causada por saques do próprio cliente, não por perdas de mercado."

Resposta consolidada:"""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "Você responde com base em DOCUMENTOS FINANCEIROS. Foque em dados, valores, datas e fatos concretos. Não adicione contexto histórico não solicitado. IMPORTANTE: Você TEM capacidade de gerar gráficos - se um gráfico foi solicitado, ele será exibido automaticamente. Não diga que não pode criar gráficos."},
                    {"role": "user", "content": consolidation_prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Erro na consolidação: {e}")
            # Fallback: retornar respostas concatenadas
            return combined_context

    async def _generate_simple_response(self, query: str, context: str, history_context: str = "") -> str:
        """Gera resposta simples quando não há agentes especializados"""
        # Incluir histórico da conversa se existir
        history_section = ""
        if history_context:
            history_section = f"""
{history_context}
Use o histórico acima para entender o contexto da conversa.

"""

        # Obter contexto fixo da Knowledge Base
        fixed_knowledge = KnowledgeBase.get_fixed_context()

        prompt = f"""Com base nos DADOS OFICIAIS abaixo, responda à pergunta do usuário.
{history_section}

══════════════════════════════════════════════════════════════════════════════
DADOS OFICIAIS DOS PORTFOLIOS (FONTE PRINCIPAL - USE ESTES DADOS):
══════════════════════════════════════════════════════════════════════════════
{fixed_knowledge}

══════════════════════════════════════════════════════════════════════════════
DOCUMENTOS COMPLEMENTARES:
══════════════════════════════════════════════════════════════════════════════
{context}

PERGUNTA: {query}

INSTRUÇÕES:
1. USE os dados das TABELAS OFICIAIS acima
2. NUNCA diga "não tem dados"

FORMATO:
- Use **negrito** para números e informações importantes
- Parágrafos curtos (2-3 linhas)
- Use bullet points para listas
- NÃO mostre dados técnicos
- Linguagem natural e amigável"""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "Você analisa documentos financeiros de um caso jurídico. Responda APENAS com dados dos documentos. Não invente contexto histórico. IMPORTANTE: O sistema TEM capacidade de gerar gráficos automaticamente - nunca diga que não pode criar gráficos."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Erro na resposta simples: {e}")
            return f"Com base nos documentos:\n\n{context[:1500]}..."
