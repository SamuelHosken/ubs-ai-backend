#!/usr/bin/env python3
"""
Script de ingestão para Complete Portfolios.
Processa os arquivos JSON completos e cria chunks maiores para preservar contexto.

HIERARQUIA DE CONHECIMENTO:
- Complete Portfolio XX.json = FONTE PRINCIPAL (prioridade máxima)
- Outros arquivos = Fontes secundárias (dados específicos)
"""
import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any

# Adicionar path do backend
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.embedding_service import EmbeddingService
from app.models.chunks import ChunkCategory, CompleteAnalysisChunkType


def load_complete_portfolio(filepath: str) -> Dict[str, Any]:
    """Carrega um arquivo Complete Portfolio JSON"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_executive_summary_chunk(data: Dict[str, Any], portfolio_num: str) -> Dict[str, Any]:
    """Cria chunk do resumo executivo (alta prioridade)"""
    resumo = data.get("resumo_executivo", {})
    documento = data.get("documento", {})

    # Criar texto rico do resumo
    content_parts = [
        f"# RESUMO EXECUTIVO - Portfolio {portfolio_num}",
        f"\n## {documento.get('titulo', '')}",
        f"**{documento.get('subtitulo', '')}**",
        f"\nConta: {documento.get('conta', '')}",
        f"\n### Pergunta Principal",
        resumo.get("pergunta", ""),
        f"\n### Resposta",
        resumo.get("resposta_curta", ""),
    ]

    # Adicionar números-chave
    numeros = resumo.get("numeros_chave", {})
    if numeros:
        content_parts.append("\n### Números-Chave")
        for key, value in numeros.items():
            key_formatted = key.replace("_", " ").title()
            content_parts.append(f"- **{key_formatted}**: {value}")

    # Adicionar decomposição
    decomp = resumo.get("decomposicao_reducao") or resumo.get("decomposicao_perda", {})
    if decomp:
        content_parts.append("\n### Decomposição")
        for key, val in decomp.items():
            if isinstance(val, dict):
                content_parts.append(f"- {key.replace('_', ' ').title()}: {val.get('valor', '')} ({val.get('percentual', '')})")

    # Adicionar responsabilidade (se existir)
    resp = resumo.get("responsabilidade", {})
    if resp:
        content_parts.append("\n### Atribuição de Responsabilidade")
        for responsavel, info in resp.items():
            if isinstance(info, dict):
                content_parts.append(f"- **{responsavel.upper()}**: {info.get('percentual', '')} - {info.get('razao', '')}")

    # Adicionar violações (se existir)
    violacoes = resumo.get("violacoes_principais", [])
    if violacoes:
        content_parts.append("\n### Violações Principais")
        for v in violacoes:
            content_parts.append(f"- {v}")

    content = "\n".join(content_parts)

    return {
        "chunk_id": f"complete_p{portfolio_num}_executive_summary",
        "content": content,
        "metadata": {
            "chunk_type": CompleteAnalysisChunkType.EXECUTIVE_SUMMARY.value,
            "portfolio_number": portfolio_num,
            "is_executive_summary": True,
            "relevance": "critical",
            "source_document": f"Complete Portfolio {portfolio_num}.json",
            "key_figures": str(numeros) if numeros else None,
        }
    }


def create_section_chunk(section: Dict[str, Any], portfolio_num: str) -> Dict[str, Any]:
    """Cria chunk de uma seção do documento"""
    section_num = section.get("numero", 0)
    section_title = section.get("titulo", "")

    content_parts = [f"# Seção {section_num}: {section_title}\n"]

    for item in section.get("conteudo", []):
        tipo = item.get("tipo", "")

        if tipo == "paragrafo":
            content_parts.append(item.get("texto", "") + "\n")

        elif tipo == "subtitulo":
            content_parts.append(f"\n## {item.get('texto', '')}\n")

        elif tipo == "destaque":
            content_parts.append(f"\n**DESTAQUE:** {item.get('texto', '')}\n")

        elif tipo == "lista":
            for li in item.get("itens", []):
                content_parts.append(f"- {li}")
            content_parts.append("")

        elif tipo == "tabela":
            content_parts.append(f"\n### {item.get('titulo', 'Tabela')}")
            if item.get("nota"):
                content_parts.append(f"*{item.get('nota')}*")

            # Headers
            colunas = item.get("colunas", [])
            content_parts.append(" | ".join(colunas))
            content_parts.append(" | ".join(["---"] * len(colunas)))

            # Rows
            for linha in item.get("linhas", []):
                if isinstance(linha, dict):
                    row_values = [str(linha.get(col, "")) for col in colunas]
                    content_parts.append(" | ".join(row_values))
            content_parts.append("")

    content = "\n".join(content_parts)

    # Determinar relevância baseado no conteúdo
    relevance = "high"
    if "conclus" in section_title.lower() or "culpa" in section_title.lower():
        relevance = "critical"
    elif "resumo" in section_title.lower() or "violaç" in section_title.lower():
        relevance = "critical"

    return {
        "chunk_id": f"complete_p{portfolio_num}_section_{section_num}",
        "content": content,
        "metadata": {
            "chunk_type": CompleteAnalysisChunkType.SECTION.value,
            "portfolio_number": portfolio_num,
            "section_number": section_num,
            "section_title": section_title,
            "relevance": relevance,
            "source_document": f"Complete Portfolio {portfolio_num}.json",
        }
    }


def create_full_narrative_chunk(data: Dict[str, Any], portfolio_num: str) -> Dict[str, Any]:
    """Cria um chunk com a narrativa completa condensada (para perguntas gerais)"""
    documento = data.get("documento", {})
    resumo = data.get("resumo_executivo", {})

    content_parts = [
        f"# ANÁLISE COMPLETA - Portfolio {portfolio_num}",
        f"\n## {documento.get('titulo', '')}",
        f"**{documento.get('subtitulo', '')}**",
        f"\nConta: {documento.get('conta', '')}",
    ]

    # Adicionar produto (se P02)
    if documento.get("produto"):
        content_parts.append(f"\nProduto: {documento.get('produto')}")
        content_parts.append(f"ISIN: {documento.get('isin', '')}")

    # Pergunta e resposta
    content_parts.extend([
        f"\n## Pergunta Principal",
        resumo.get("pergunta", ""),
        f"\n## Resposta",
        resumo.get("resposta_curta", ""),
    ])

    # Resumo de cada seção
    for section in data.get("secoes", []):
        section_title = section.get("titulo", "")
        content_parts.append(f"\n### {section_title}")

        # Pegar apenas destaques e parágrafos importantes
        for item in section.get("conteudo", []):
            if item.get("tipo") == "destaque":
                content_parts.append(f"**{item.get('texto', '')}**")
            elif item.get("tipo") == "paragrafo" and len(item.get("texto", "")) > 100:
                content_parts.append(item.get("texto", "")[:500] + "...")

    content = "\n".join(content_parts)

    return {
        "chunk_id": f"complete_p{portfolio_num}_full_narrative",
        "content": content,
        "metadata": {
            "chunk_type": CompleteAnalysisChunkType.FULL_NARRATIVE.value,
            "portfolio_number": portfolio_num,
            "relevance": "critical",
            "source_document": f"Complete Portfolio {portfolio_num}.json",
        }
    }


def process_complete_portfolio(filepath: str, embedding_service: EmbeddingService) -> int:
    """Processa um arquivo Complete Portfolio e adiciona ao ChromaDB"""
    print(f"\n{'='*60}")
    print(f"Processando: {filepath}")
    print(f"{'='*60}")

    # Extrair número do portfolio do nome do arquivo
    filename = os.path.basename(filepath)
    if "01" in filename:
        portfolio_num = "01"
    elif "02" in filename:
        portfolio_num = "02"
    else:
        portfolio_num = "XX"

    # Carregar dados
    data = load_complete_portfolio(filepath)

    chunks = []

    # 1. Chunk do resumo executivo (PRIORIDADE MÁXIMA)
    print("  Criando chunk do resumo executivo...")
    chunks.append(create_executive_summary_chunk(data, portfolio_num))

    # 2. Chunks de cada seção (ALTA PRIORIDADE)
    print("  Criando chunks das seções...")
    for section in data.get("secoes", []):
        chunks.append(create_section_chunk(section, portfolio_num))

    # 3. Chunk da narrativa completa (para perguntas gerais)
    print("  Criando chunk da narrativa completa...")
    chunks.append(create_full_narrative_chunk(data, portfolio_num))

    # Adicionar ao ChromaDB
    print(f"\n  Adicionando {len(chunks)} chunks ao ChromaDB...")
    added = embedding_service.add_chunks_batch(
        category=ChunkCategory.COMPLETE_ANALYSIS,
        chunks=chunks,
        batch_size=10
    )

    print(f"  Adicionados {added} chunks para Portfolio {portfolio_num}")
    return added


def main():
    """Função principal"""
    print("\n" + "="*60)
    print("INGESTÃO DE COMPLETE PORTFOLIOS")
    print("Fonte Principal de Conhecimento")
    print("="*60)

    # Inicializar serviço
    embedding_service = EmbeddingService()

    # Limpar collection existente
    print("\nLimpando collection complete_analysis...")
    try:
        embedding_service.clear_collection(ChunkCategory.COMPLETE_ANALYSIS)
        print("  Collection limpa com sucesso!")
    except Exception as e:
        print(f"  Aviso: {e}")

    # Diretório dos arquivos
    forensic_dir = Path(__file__).parent.parent / "data" / "raw" / "forensic"

    # Encontrar arquivos Complete Portfolio
    complete_files = list(forensic_dir.glob("Complete Portfolio*.json"))

    if not complete_files:
        print("\nNenhum arquivo Complete Portfolio encontrado!")
        print(f"Diretório verificado: {forensic_dir}")
        return

    print(f"\nEncontrados {len(complete_files)} arquivos:")
    for f in complete_files:
        print(f"  - {f.name}")

    # Processar cada arquivo
    total_chunks = 0
    for filepath in complete_files:
        total_chunks += process_complete_portfolio(str(filepath), embedding_service)

    # Estatísticas finais
    print("\n" + "="*60)
    print("INGESTÃO CONCLUÍDA")
    print("="*60)
    print(f"Total de chunks adicionados: {total_chunks}")

    stats = embedding_service.get_all_collection_stats()
    print("\nEstatísticas das collections:")
    for name, count in stats.items():
        priority = " (PRIORIDADE MÁXIMA)" if "complete" in name else ""
        print(f"  - {name}: {count} chunks{priority}")


if __name__ == "__main__":
    main()
