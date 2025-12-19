#!/usr/bin/env python3
"""
Script de ingestão completa de todos os dados forenses.
Processa statements, fees, timeline, documentos oficiais UBS e análises forenses.
"""
import sys
import os
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.services.embedding_service import EmbeddingService
from app.models.chunks import ChunkCategory
from app.processors import (
    StatementsProcessor,
    FeesProcessor,
    TimelineProcessor,
    ForensicProcessor,
    UBSDocsProcessor
)


def print_header(text: str):
    """Imprime header formatado"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_stats(stats: dict):
    """Imprime estatísticas"""
    print("\n" + "-" * 40)
    print("ESTATÍSTICAS:")
    print("-" * 40)
    for name, count in stats.items():
        print(f"  {name}: {count} chunks")
    print("-" * 40)
    print(f"  TOTAL: {sum(stats.values())} chunks")


def ingest_statements(embedding_service: EmbeddingService, base_path: Path) -> int:
    """Ingere statements"""
    print_header("📊 Processando Statements...")

    processor = StatementsProcessor(str(base_path / "statements"))
    chunks = processor.process_all()

    if chunks:
        chunk_dicts = [
            {
                "chunk_id": c.chunk_id,
                "content": c.content,
                "metadata": c.model_dump(exclude={"content", "chunk_id", "content_pt"})
            }
            for c in chunks
        ]

        embedding_service.add_chunks_batch(ChunkCategory.FACTS, chunk_dicts)

    print(f"\n✅ {len(chunks)} chunks de statements adicionados")
    return len(chunks)


def ingest_fees(embedding_service: EmbeddingService, base_path: Path) -> int:
    """Ingere fees"""
    print_header("💰 Processando Fees...")

    processor = FeesProcessor(str(base_path / "fees"))
    chunks = processor.process_all()

    if chunks:
        chunk_dicts = [
            {
                "chunk_id": c.chunk_id,
                "content": c.content,
                "metadata": c.model_dump(exclude={"content", "chunk_id", "content_pt"})
            }
            for c in chunks
        ]

        embedding_service.add_chunks_batch(ChunkCategory.FACTS, chunk_dicts)

    print(f"\n✅ {len(chunks)} chunks de fees adicionados")
    return len(chunks)


def ingest_timeline(embedding_service: EmbeddingService, base_path: Path) -> dict:
    """Ingere timeline"""
    print_header("📅 Processando Timeline...")

    processor = TimelineProcessor(str(base_path / "timeline"))
    results = processor.process_all()

    stats = {"context": 0, "client": 0}

    # Chunks de contexto histórico
    context_chunks = results.get("context", [])
    if context_chunks:
        chunk_dicts = [
            {
                "chunk_id": c.chunk_id,
                "content": c.content,
                "metadata": c.model_dump(exclude={"content", "chunk_id", "content_pt"})
            }
            for c in context_chunks
        ]
        embedding_service.add_chunks_batch(ChunkCategory.CONTEXT, chunk_dicts)
        stats["context"] = len(context_chunks)
        print(f"  ✅ {len(context_chunks)} chunks de contexto histórico")

    # Chunks do cliente
    client_chunks = results.get("client", [])
    if client_chunks:
        chunk_dicts = [
            {
                "chunk_id": c.chunk_id,
                "content": c.content,
                "metadata": c.model_dump(exclude={"content", "chunk_id", "content_pt"})
            }
            for c in client_chunks
        ]
        embedding_service.add_chunks_batch(ChunkCategory.CLIENT, chunk_dicts)
        stats["client"] = len(client_chunks)
        print(f"  ✅ {len(client_chunks)} chunks de timeline do cliente")

    return stats


def ingest_forensic(embedding_service: EmbeddingService, base_path: Path) -> int:
    """Ingere análises forenses"""
    print_header("🔍 Processando Análises Forenses...")

    processor = ForensicProcessor(str(base_path / "forensic"))
    chunks = processor.process_all()

    if chunks:
        chunk_dicts = [
            {
                "chunk_id": c.chunk_id,
                "content": c.content,
                "metadata": c.model_dump(exclude={"content", "chunk_id", "content_pt"})
            }
            for c in chunks
        ]

        embedding_service.add_chunks_batch(ChunkCategory.FORENSIC, chunk_dicts)

    print(f"\n✅ {len(chunks)} chunks forenses adicionados")
    return len(chunks)


def ingest_ubs_official(embedding_service: EmbeddingService, base_path: Path) -> int:
    """Ingere documentos oficiais da UBS"""
    print_header("📜 Processando Documentos Oficiais UBS...")

    processor = UBSDocsProcessor(str(base_path / "ubs_official"))
    chunks = processor.process_all()

    if chunks:
        chunk_dicts = [
            {
                "chunk_id": c.chunk_id,
                "content": c.content,
                "metadata": c.model_dump(exclude={"content", "chunk_id", "content_pt"})
            }
            for c in chunks
        ]

        embedding_service.add_chunks_batch(ChunkCategory.UBS_OFFICIAL, chunk_dicts)

    print(f"\n✅ {len(chunks)} chunks de docs oficiais UBS adicionados")
    return len(chunks)


def main():
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "🚀 INGESTÃO FORENSE - RAG UBS" + " " * 18 + "║")
    print("╚" + "═" * 58 + "╝")

    # Caminho base dos dados
    base_path = Path(__file__).parent.parent / "data" / "raw"

    if not base_path.exists():
        print(f"\n❌ Pasta de dados não encontrada: {base_path}")
        print("Crie a pasta e adicione os documentos.")
        return

    # Inicializar serviço de embeddings
    print("\n🔧 Inicializando serviço de embeddings...")
    embedding_service = EmbeddingService()

    # Limpar collections antes de popular (evita duplicatas)
    print("\n🧹 Limpando collections existentes...")
    for category in ChunkCategory:
        try:
            embedding_service.clear_collection(category)
            print(f"  ✓ {category.value} limpa")
        except Exception as e:
            print(f"  ⚠️ {category.value}: {e}")

    # Estatísticas
    stats = {}

    # 1. Statements
    if (base_path / "statements").exists():
        stats["statements"] = ingest_statements(embedding_service, base_path)
    else:
        print("\n⚠️  Pasta statements/ não encontrada, pulando...")

    # 2. Fees
    if (base_path / "fees").exists():
        stats["fees"] = ingest_fees(embedding_service, base_path)
    else:
        print("\n⚠️  Pasta fees/ não encontrada, pulando...")

    # 3. Timeline
    if (base_path / "timeline").exists():
        timeline_stats = ingest_timeline(embedding_service, base_path)
        stats["context"] = timeline_stats.get("context", 0)
        stats["client"] = timeline_stats.get("client", 0)
    else:
        print("\n⚠️  Pasta timeline/ não encontrada, pulando...")

    # 4. Forensic
    if (base_path / "forensic").exists():
        stats["forensic"] = ingest_forensic(embedding_service, base_path)
    else:
        print("\n⚠️  Pasta forensic/ não encontrada, pulando...")

    # 5. Documentos oficiais UBS
    if (base_path / "ubs_official").exists():
        stats["ubs_official"] = ingest_ubs_official(embedding_service, base_path)
    else:
        print("\n⚠️  Pasta ubs_official/ não encontrada, pulando...")

    # Resumo final
    print_header("✅ INGESTÃO COMPLETA!")
    print_stats(stats)

    # Estatísticas do ChromaDB
    print("\n📊 Estatísticas do ChromaDB:")
    chroma_stats = embedding_service.get_all_collection_stats()
    for collection, count in chroma_stats.items():
        if count > 0:
            print(f"  {collection}: {count} documentos")

    print("\n" + "=" * 60)
    print("  🎉 Pronto para usar o RAG Forense!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
