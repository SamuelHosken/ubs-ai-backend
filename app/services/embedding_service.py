"""
Embedding Service com suporte a múltiplas collections para RAG Forense.
"""
from openai import OpenAI
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Optional, Any, Union
from app.core.config import settings
from app.models.chunks import ChunkCategory
import os


class EmbeddingService:
    """Serviço de embeddings com múltiplas collections"""

    # Nomes das collections
    COLLECTIONS = {
        # PRIORIDADE MÁXIMA - Fonte principal de conhecimento
        ChunkCategory.COMPLETE_ANALYSIS: "complete_analysis",

        # Fontes secundárias
        ChunkCategory.FACTS: "portfolio_facts",
        ChunkCategory.FORENSIC: "forensic_analysis",
        ChunkCategory.CONTEXT: "historical_context",
        ChunkCategory.CLIENT: "client_timeline",
        ChunkCategory.UBS_OFFICIAL: "ubs_official_docs",
    }

    # Collection prioritária (sempre buscar primeiro)
    PRIMARY_COLLECTION = ChunkCategory.COMPLETE_ANALYSIS

    # Collection legada (compatibilidade)
    LEGACY_COLLECTION = "ubs_documents"

    def __init__(self):
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "text-embedding-3-small"

        # Garantir que o diretório existe
        os.makedirs(settings.CHROMA_PERSIST_DIRECTORY, exist_ok=True)

        # Configurar ChromaDB com persistência
        self.chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIRECTORY
        )

        # Collection legada (compatibilidade com código existente)
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.LEGACY_COLLECTION,
            metadata={"description": "UBS Portfolio Documents (Legacy)"}
        )

        # Inicializar collections forenses
        self.collections: Dict[ChunkCategory, Any] = {}
        for category, name in self.COLLECTIONS.items():
            self.collections[category] = self.chroma_client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )

    def create_embedding(self, text: str) -> List[float]:
        """Cria embedding usando OpenAI"""
        response = self.openai_client.embeddings.create(
            model=self.model,
            input=text
        )
        return response.data[0].embedding

    # ============================================================
    # MÉTODOS LEGADOS (compatibilidade)
    # ============================================================

    def add_document_chunk(self, chunk_id: str, text: str, metadata: dict):
        """Adiciona chunk ao vector DB (collection legada)"""
        embedding = self.create_embedding(text)

        self.collection.add(
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata],
            ids=[chunk_id]
        )

    def search_similar(self, query: str, n_results: int = 5) -> dict:
        """Busca chunks similares à query (collection legada)"""
        query_embedding = self.create_embedding(query)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )

        return {
            "documents": results["documents"][0] if results["documents"] else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] else [],
            "distances": results["distances"][0] if results["distances"] else []
        }

    def get_collection_count(self) -> int:
        """Retorna o número de documentos na collection legada"""
        return self.collection.count()

    # ============================================================
    # NOVOS MÉTODOS (múltiplas collections)
    # ============================================================

    def add_chunk(
        self,
        category: ChunkCategory,
        chunk_id: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Adiciona um chunk a uma collection específica"""
        collection = self.collections[category]

        # Criar embedding
        embedding = self.create_embedding(content)

        # Limpar metadata (ChromaDB não aceita None)
        clean_metadata = {k: v for k, v in metadata.items() if v is not None}

        # Converter listas para strings (ChromaDB limitation)
        for key, value in clean_metadata.items():
            if isinstance(value, list):
                clean_metadata[key] = str(value)
            elif isinstance(value, dict):
                clean_metadata[key] = str(value)

        # Adicionar à collection
        collection.add(
            ids=[chunk_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[clean_metadata]
        )

    def add_chunks_batch(
        self,
        category: ChunkCategory,
        chunks: List[Dict[str, Any]],
        batch_size: int = 50
    ) -> int:
        """Adiciona múltiplos chunks de uma vez"""
        from datetime import date, datetime

        collection = self.collections[category]
        total_added = 0

        # Processar em batches
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]

            ids = []
            documents = []
            metadatas = []
            embeddings = []

            for chunk in batch:
                ids.append(chunk["chunk_id"])
                documents.append(chunk["content"])

                # Limpar metadata
                meta = chunk.get("metadata", {})
                clean_meta = {}

                for k, v in meta.items():
                    if v is None:
                        continue
                    # Converter datas para string
                    if isinstance(v, (date, datetime)):
                        clean_meta[k] = v.isoformat()
                    # Converter tipos complexos para string
                    elif isinstance(v, (list, dict)):
                        clean_meta[k] = str(v)
                    # Manter tipos primitivos
                    elif isinstance(v, (str, int, float, bool)):
                        clean_meta[k] = v
                    else:
                        clean_meta[k] = str(v)

                metadatas.append(clean_meta)
                embeddings.append(self.create_embedding(chunk["content"]))

            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )

            total_added += len(batch)
            print(f"  Adicionados {total_added}/{len(chunks)} chunks...")

        return total_added

    def search_collection(
        self,
        category: ChunkCategory,
        query: str,
        n_results: int = 5,
        where: Optional[Dict] = None,
        where_document: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Busca em uma collection específica"""
        collection = self.collections[category]

        # Criar embedding da query
        query_embedding = self.create_embedding(query)

        # Buscar
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=["documents", "metadatas", "distances"]
        )

        return {
            "documents": results["documents"][0] if results["documents"] else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] else [],
            "distances": results["distances"][0] if results["distances"] else []
        }

    def search_multiple_collections(
        self,
        query: str,
        categories: List[ChunkCategory],
        n_results_per_collection: int = 3,
        filters: Optional[Dict[ChunkCategory, Dict]] = None
    ) -> Dict[ChunkCategory, Dict[str, Any]]:
        """Busca em múltiplas collections simultaneamente"""
        results = {}

        for category in categories:
            where_filter = filters.get(category) if filters else None
            results[category] = self.search_collection(
                category=category,
                query=query,
                n_results=n_results_per_collection,
                where=where_filter
            )

        return results

    def search_all(
        self,
        query: str,
        n_results_per_collection: int = 3
    ) -> Dict[ChunkCategory, Dict[str, Any]]:
        """Busca em TODAS as collections"""
        return self.search_multiple_collections(
            query=query,
            categories=list(ChunkCategory),
            n_results_per_collection=n_results_per_collection
        )

    def search_with_priority(
        self,
        query: str,
        n_primary: int = 10,
        n_secondary: int = 3,
        secondary_categories: List[ChunkCategory] = None
    ) -> Dict[ChunkCategory, Dict[str, Any]]:
        """
        Busca hierárquica: primeiro na fonte principal, depois nas secundárias.
        SEMPRE prioriza COMPLETE_ANALYSIS.
        """
        results = {}

        # 1. SEMPRE buscar primeiro em COMPLETE_ANALYSIS (prioridade máxima)
        primary_results = self.search_collection(
            category=self.PRIMARY_COLLECTION,
            query=query,
            n_results=n_primary
        )
        results[self.PRIMARY_COLLECTION] = primary_results

        # 2. Se encontrou resultados relevantes na fonte principal, usar menos da secundária
        primary_has_results = len(primary_results.get("documents", [])) > 0

        # 3. Buscar em collections secundárias
        if secondary_categories is None:
            secondary_categories = [
                ChunkCategory.FACTS,
                ChunkCategory.FORENSIC,
            ]

        # Ajustar quantidade baseado na qualidade da busca primária
        adjusted_n = n_secondary if not primary_has_results else max(1, n_secondary // 2)

        for category in secondary_categories:
            if category != self.PRIMARY_COLLECTION:
                results[category] = self.search_collection(
                    category=category,
                    query=query,
                    n_results=adjusted_n
                )

        return results

    def get_all_collection_stats(self) -> Dict[str, int]:
        """Retorna estatísticas de todas as collections"""
        stats = {}

        # Collection legada
        stats[self.LEGACY_COLLECTION] = self.collection.count()

        # Collections forenses
        for category, collection in self.collections.items():
            stats[category.value] = collection.count()

        return stats

    def delete_collection(self, category: ChunkCategory) -> None:
        """Deleta uma collection (para reprocessamento)"""
        collection_name = self.COLLECTIONS[category]
        self.chroma_client.delete_collection(collection_name)

        # Recriar vazia
        self.collections[category] = self.chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def clear_collection(self, category: ChunkCategory) -> None:
        """Limpa todos os documentos de uma collection"""
        collection = self.collections[category]
        # Pegar todos os IDs
        all_ids = collection.get()["ids"]
        if all_ids:
            collection.delete(ids=all_ids)
