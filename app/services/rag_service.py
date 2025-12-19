from openai import OpenAI
from typing import List, Dict, Optional
from app.core.config import settings
from .embedding_service import EmbeddingService
from .chart_generator import ChartGenerator

class RAGService:
    def __init__(self, embedding_service: EmbeddingService):
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.embedding_service = embedding_service
        self.model = settings.OPENAI_MODEL
        self.chart_generator = ChartGenerator()

    def generate_response(self, query: str, conversation_history: List[Dict] = None) -> Dict:
        """Gera resposta usando RAG com suporte a charts"""

        # 1. Buscar documentos relevantes
        search_results = self.embedding_service.search_similar(query, n_results=5)

        # 2. Construir contexto
        context = self._build_context(search_results)

        # 3. Criar prompt do sistema
        system_prompt = self._create_system_prompt(context)

        # 4. Preparar mensagens
        messages = [{"role": "system", "content": system_prompt}]

        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": query})

        # 5. Chamar OpenAI
        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            max_tokens=2000
        )

        # 6. Processar resposta
        ai_response = response.choices[0].message.content

        result = {
            "response": ai_response,
            "sources": self._extract_sources(search_results),
            "tokens_used": response.usage.total_tokens
        }

        # 7. Detectar se precisa de gráfico e gerar
        chart_type = self.chart_generator.detect_chart_intent(query)
        if chart_type:
            chart_data = self.chart_generator.generate_chart_from_context(
                chart_type, context, query
            )
            if chart_data:
                result["chart"] = chart_data

        return result

    def _build_context(self, search_results: dict) -> str:
        """Constrói contexto a partir dos documentos encontrados"""
        if not search_results["documents"]:
            return "Nenhum documento relevante encontrado."

        context_parts = []

        for doc, metadata in zip(search_results["documents"], search_results["metadatas"]):
            source_info = f"[Documento: {metadata.get('filename', 'Unknown')}]"
            if metadata.get('page'):
                source_info += f" [Página: {metadata['page']}]"

            context_parts.append(f"{source_info}\n{doc}\n")

        return "\n---\n".join(context_parts)

    def _create_system_prompt(self, context: str) -> str:
        """Cria prompt do sistema com contexto"""
        return f"""Você é um assistente especializado em análise de portfólios de investimento da UBS.

Seu papel é responder perguntas sobre a conta de investimento do cliente com base EXCLUSIVAMENTE nos documentos fornecidos.

REGRAS IMPORTANTES:
1. Use APENAS as informações dos documentos fornecidos
2. Se não tiver informação nos documentos, diga claramente "Não encontrei essa informação nos documentos disponíveis"
3. Sempre cite o documento fonte ao responder (ex: "Segundo o documento X, página Y...")
4. Quando relevante, sugira visualizações (gráficos/tabelas) que podem ajudar
5. Seja preciso com números e datas
6. Use linguagem clara e profissional

DOCUMENTOS DISPONÍVEIS:
{context}

Responda à pergunta do cliente de forma completa, mas concisa."""

    def _extract_sources(self, search_results: dict) -> List[Dict]:
        """Extrai informações sobre as fontes utilizadas"""
        sources = []

        if not search_results["metadatas"]:
            return sources

        seen_files = set()
        for metadata in search_results["metadatas"]:
            filename = metadata.get("filename", "Unknown")
            if filename not in seen_files:
                seen_files.add(filename)
                sources.append({
                    "filename": filename,
                    "page": metadata.get("page"),
                    "document_type": metadata.get("type", "unknown"),
                    "relevance": "high"
                })

        return sources
