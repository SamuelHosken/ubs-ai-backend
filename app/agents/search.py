"""
Search Agent - Busca em múltiplas collections do RAG Forense.

HIERARQUIA DE CONHECIMENTO:
1. COMPLETE_ANALYSIS - Fonte principal (SEMPRE buscar primeiro)
2. FACTS, FORENSIC - Fontes secundárias (dados específicos)
3. CONTEXT, CLIENT, UBS_OFFICIAL - Fontes terciárias (quando solicitado)
"""
from typing import Dict, Optional, List
import cohere
from app.services.embedding_service import EmbeddingService
from app.models.chunks import ChunkCategory
from app.core.config import settings
import os


class SearchAgent:
    """Agente de busca com suporte a múltiplas collections e hierarquia de prioridade"""

    # Fonte principal de conhecimento
    PRIMARY_SOURCE = ChunkCategory.COMPLETE_ANALYSIS

    # Fontes secundárias (dados específicos)
    SECONDARY_SOURCES = [ChunkCategory.FACTS, ChunkCategory.FORENSIC]

    # Fontes terciárias (contexto adicional)
    TERTIARY_SOURCES = [ChunkCategory.CONTEXT, ChunkCategory.CLIENT, ChunkCategory.UBS_OFFICIAL]

    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
        cohere_key = os.getenv("COHERE_API_KEY")
        self.cohere_client = cohere.Client(cohere_key) if cohere_key else None

    async def search(
        self,
        query: str,
        n_results: int = 5,
        use_rerank: bool = True
    ) -> Dict:
        """Busca na collection legada (compatibilidade)"""
        initial_results = self.embedding_service.search_similar(
            query=query,
            n_results=n_results * 2 if use_rerank else n_results
        )

        if use_rerank and self.cohere_client and initial_results["documents"]:
            try:
                reranked = self.cohere_client.rerank(
                    model="rerank-multilingual-v2.0",
                    query=query,
                    documents=initial_results["documents"],
                    top_n=n_results
                )

                reranked_docs = []
                reranked_metadata = []

                for result in reranked.results:
                    idx = result.index
                    reranked_docs.append(initial_results["documents"][idx])
                    reranked_metadata.append(initial_results["metadatas"][idx])

                return {
                    "documents": reranked_docs,
                    "metadatas": reranked_metadata,
                    "reranked": True
                }
            except Exception as e:
                print(f"Rerank error: {e}")

        return initial_results

    async def search_forensic(
        self,
        query: str,
        categories: List[ChunkCategory] = None,
        n_results_per_collection: int = 3,
        use_rerank: bool = True
    ) -> Dict[ChunkCategory, Dict]:
        """
        Busca em múltiplas collections forenses.
        Retorna resultados organizados por categoria.

        IMPORTANTE: SEMPRE inclui COMPLETE_ANALYSIS como fonte principal.
        """
        if categories is None:
            # Por padrão, busca nas fontes principais e secundárias
            categories = [
                ChunkCategory.COMPLETE_ANALYSIS,  # SEMPRE incluir fonte principal
                ChunkCategory.FACTS,
                ChunkCategory.FORENSIC,
            ]

        # Garantir que COMPLETE_ANALYSIS está sempre incluído
        if ChunkCategory.COMPLETE_ANALYSIS not in categories:
            categories = [ChunkCategory.COMPLETE_ANALYSIS] + list(categories)

        # Buscar em todas as collections
        results = self.embedding_service.search_multiple_collections(
            query=query,
            categories=categories,
            n_results_per_collection=n_results_per_collection * 2 if use_rerank else n_results_per_collection
        )

        # Aplicar rerank se disponível
        if use_rerank and self.cohere_client:
            results = self._rerank_results(query, results, n_results_per_collection)

        return results

    async def search_hierarchical(
        self,
        query: str,
        n_primary: int = 8,
        n_secondary: int = 3,
        include_tertiary: bool = False,
        use_rerank: bool = True
    ) -> Dict[ChunkCategory, Dict]:
        """
        Busca hierárquica com prioridade.

        1. SEMPRE busca primeiro em COMPLETE_ANALYSIS (fonte principal)
        2. Complementa com FACTS e FORENSIC (dados específicos)
        3. Opcionalmente adiciona CONTEXT, CLIENT, UBS_OFFICIAL

        Esta é a busca RECOMENDADA para todas as queries.
        """
        results = {}

        # 1. FONTE PRINCIPAL - COMPLETE_ANALYSIS (prioridade máxima)
        primary_results = self.embedding_service.search_collection(
            category=self.PRIMARY_SOURCE,
            query=query,
            n_results=n_primary * 2 if use_rerank else n_primary
        )

        if use_rerank and self.cohere_client and primary_results.get("documents"):
            primary_results = self._rerank_single(query, primary_results, n_primary)

        results[self.PRIMARY_SOURCE] = primary_results

        # Verificar se encontrou contexto relevante na fonte principal
        primary_has_context = len(primary_results.get("documents", [])) >= 2

        # 2. FONTES SECUNDÁRIAS - FACTS e FORENSIC
        # Ajustar quantidade baseado na qualidade da fonte principal
        adjusted_n = n_secondary if not primary_has_context else max(1, n_secondary // 2)

        for category in self.SECONDARY_SOURCES:
            cat_results = self.embedding_service.search_collection(
                category=category,
                query=query,
                n_results=adjusted_n * 2 if use_rerank else adjusted_n
            )

            if use_rerank and self.cohere_client and cat_results.get("documents"):
                cat_results = self._rerank_single(query, cat_results, adjusted_n)

            results[category] = cat_results

        # 3. FONTES TERCIÁRIAS (opcional)
        if include_tertiary:
            for category in self.TERTIARY_SOURCES:
                cat_results = self.embedding_service.search_collection(
                    category=category,
                    query=query,
                    n_results=2  # Poucos resultados de contexto adicional
                )
                results[category] = cat_results

        return results

    def _rerank_single(
        self,
        query: str,
        results: Dict,
        top_n: int
    ) -> Dict:
        """Aplica reranking a um único resultado"""
        docs = results.get("documents", [])
        metas = results.get("metadatas", [])

        if not docs:
            return results

        try:
            reranked = self.cohere_client.rerank(
                model="rerank-multilingual-v2.0",
                query=query,
                documents=docs,
                top_n=min(top_n, len(docs))
            )

            reranked_docs = []
            reranked_metas = []

            for result in reranked.results:
                idx = result.index
                reranked_docs.append(docs[idx])
                if idx < len(metas):
                    reranked_metas.append(metas[idx])

            return {
                "documents": reranked_docs,
                "metadatas": reranked_metas,
                "reranked": True
            }
        except Exception as e:
            print(f"Rerank error: {e}")
            return results

    async def search_facts(self, query: str, n_results: int = 5) -> Dict:
        """Busca apenas em fatos financeiros (statements + fees)"""
        return self.embedding_service.search_collection(
            category=ChunkCategory.FACTS,
            query=query,
            n_results=n_results
        )

    async def search_context(self, query: str, n_results: int = 5) -> Dict:
        """Busca em contexto histórico"""
        results = self.embedding_service.search_multiple_collections(
            query=query,
            categories=[ChunkCategory.CONTEXT, ChunkCategory.CLIENT],
            n_results_per_collection=n_results
        )
        return results

    async def search_violations(self, query: str, n_results: int = 5) -> Dict:
        """Busca em análises forenses e documentos oficiais"""
        results = self.embedding_service.search_multiple_collections(
            query=query,
            categories=[ChunkCategory.FORENSIC, ChunkCategory.UBS_OFFICIAL],
            n_results_per_collection=n_results
        )
        return results

    def _rerank_results(
        self,
        query: str,
        results: Dict[ChunkCategory, Dict],
        top_n: int
    ) -> Dict[ChunkCategory, Dict]:
        """Aplica reranking aos resultados de cada collection"""
        reranked_results = {}

        for category, cat_results in results.items():
            docs = cat_results.get("documents", [])
            metas = cat_results.get("metadatas", [])

            if not docs:
                reranked_results[category] = cat_results
                continue

            try:
                reranked = self.cohere_client.rerank(
                    model="rerank-multilingual-v2.0",
                    query=query,
                    documents=docs,
                    top_n=min(top_n, len(docs))
                )

                reranked_docs = []
                reranked_metas = []

                for result in reranked.results:
                    idx = result.index
                    reranked_docs.append(docs[idx])
                    if idx < len(metas):
                        reranked_metas.append(metas[idx])

                reranked_results[category] = {
                    "documents": reranked_docs,
                    "metadatas": reranked_metas,
                    "reranked": True
                }
            except Exception as e:
                print(f"Rerank error for {category}: {e}")
                reranked_results[category] = cat_results

        return reranked_results

    def format_context_for_llm(self, results: Dict[ChunkCategory, Dict]) -> str:
        """
        Formata resultados de múltiplas collections para o LLM.

        HIERARQUIA DE PRIORIDADE:
        1. COMPLETE_ANALYSIS - FONTE PRINCIPAL (mostrar primeiro e com destaque)
        2. Outras collections - Dados complementares
        """
        formatted = ""

        # 1. SEMPRE mostrar COMPLETE_ANALYSIS primeiro (FONTE PRINCIPAL)
        if self.PRIMARY_SOURCE in results:
            primary_results = results[self.PRIMARY_SOURCE]
            docs = primary_results.get("documents", [])
            metas = primary_results.get("metadatas", [])

            if docs:
                formatted += "\n" + "=" * 70 + "\n"
                formatted += ">>> FONTE PRINCIPAL DE CONHECIMENTO - USE ESTES DADOS <<<\n"
                formatted += "=" * 70 + "\n\n"

                for doc, meta in zip(docs, metas or [{}] * len(docs)):
                    source = meta.get("source_document", "Complete Portfolio") if meta else "Complete Portfolio"
                    formatted += f"[{source}]\n{doc}\n\n---\n\n"

                formatted += "=" * 70 + "\n"
                formatted += ">>> FIM DA FONTE PRINCIPAL <<<\n"
                formatted += "=" * 70 + "\n\n"

        # 2. Mostrar outras collections como DADOS COMPLEMENTARES
        has_secondary = False
        for category, cat_results in results.items():
            if category == self.PRIMARY_SOURCE:
                continue

            docs = cat_results.get("documents", [])
            metas = cat_results.get("metadatas", [])

            if not docs:
                continue

            if not has_secondary:
                formatted += "\n--- DADOS COMPLEMENTARES (use apenas se necessário) ---\n\n"
                has_secondary = True

            category_name = category.value.upper().replace("_", " ")
            formatted += f"[{category_name}]\n"

            # Limitar dados complementares para não "afogar" a fonte principal
            for doc, meta in zip(docs[:3], (metas or [{}] * len(docs))[:3]):
                source = meta.get("source_document", "Documento") if meta else "Documento"
                # Truncar documentos secundários se muito longos
                doc_truncated = doc[:1000] + "..." if len(doc) > 1000 else doc
                formatted += f"{doc_truncated}\n\n"

        return formatted if formatted else "Nenhum documento relevante encontrado."
