"""
Processador de Mandate Fees.
Converte JSON de taxas em chunks para o RAG.
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.models.chunks import (
    FeesChunk,
    FinancialFactChunk,
    FactsChunkType,
    create_chunk_id
)


class FeesProcessor:
    """Processa JSON de Mandate Fees e gera chunks"""

    def __init__(self, fees_dir: str = "data/raw/fees"):
        self.fees_dir = Path(fees_dir)

    def process_all(self) -> List[FinancialFactChunk]:
        """Processa todos os arquivos de fees"""
        all_chunks = []

        for json_file in self.fees_dir.glob("*.json"):
            try:
                chunks = self.process_fees_file(json_file)
                all_chunks.extend(chunks)
                print(f"  ✓ {json_file.name}: {len(chunks)} chunks")
            except Exception as e:
                print(f"  ✗ {json_file.name}: {e}")

        return all_chunks

    def process_fees_file(self, json_path: Path) -> List[FinancialFactChunk]:
        """Processa um arquivo de fees"""
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        chunks = []

        metadata = data.get("metadata", {})
        portfolio_number = metadata.get("portfolio_number", "")
        source_doc = json_path.stem

        # 1. Chunk de resumo geral
        summary_chunk = self._create_summary_chunk(data, portfolio_number, source_doc)
        if summary_chunk:
            chunks.append(summary_chunk)

        # 2. Chunks por período (trimestre)
        fee_chunks = self._create_fee_chunks(data, portfolio_number, source_doc)
        chunks.extend(fee_chunks)

        # 3. Chunk de evolução de taxas
        rate_chunk = self._create_rate_evolution_chunk(data, portfolio_number, source_doc)
        if rate_chunk:
            chunks.append(rate_chunk)

        return chunks

    def _create_summary_chunk(
        self, data: Dict, portfolio_number: str, source_doc: str
    ) -> Optional[FinancialFactChunk]:
        """Cria chunk de resumo das taxas"""
        metadata = data.get("metadata", {})
        fees = data.get("fees", [])

        if not fees:
            return None

        period = metadata.get("period_covered", {})
        total_periods = metadata.get("total_periods", len(fees))

        # Calcular totais
        total_chf = sum(f.get("amount_chf", 0) or 0 for f in fees)
        total_eur = sum(f.get("amount_eur", 0) or 0 for f in fees)
        avg_rate = sum(f.get("rate_pct", 0) or 0 for f in fees) / len(fees) if fees else 0

        # Período
        start_date = period.get("start", "")
        end_date = period.get("end", "")

        content = f"""RESUMO DE TAXAS DE GESTÃO (MANDATE FEES)

Portfólio: {portfolio_number}
Período: {start_date} até {end_date}
Total de Períodos: {total_periods} trimestres

TOTAIS COBRADOS:
- CHF {total_chf:,.2f}
- EUR {total_eur:,.2f}

TAXA MÉDIA ANUAL: {avg_rate:.2f}% a.a.

TIPO: {metadata.get('fee_type', 'Management Fee')}
MÉTODO: {metadata.get('calculation_method', 'Percentual sobre valor do portfólio')}

⚠️ OBSERVAÇÃO: Estas taxas foram cobradas mesmo durante períodos de perdas significativas.
"""

        return FinancialFactChunk(
            chunk_id=create_chunk_id("facts", "fees_summary", f"{portfolio_number}"),
            chunk_type=FactsChunkType.FEES_SUMMARY,
            content=content,
            source_document=source_doc,
            portfolio_number=portfolio_number,
            portfolio_type="01",
            fee_amount_chf=total_chf,
            fee_amount_eur=total_eur,
            fee_rate_pct=avg_rate,
            relevance="high"
        )

    def _create_fee_chunks(
        self, data: Dict, portfolio_number: str, source_doc: str
    ) -> List[FinancialFactChunk]:
        """Cria chunks para cada período de cobrança"""
        chunks = []
        fees = data.get("fees", [])

        for fee in fees:
            period = fee.get("period", "")
            year = fee.get("year")
            quarter = fee.get("quarter")
            amount_chf = fee.get("amount_chf", 0)
            amount_eur = fee.get("amount_eur", 0)
            rate = fee.get("rate_pct", 0)
            basis = fee.get("basis_chf", 0)

            content = f"""TAXA DE GESTÃO - {period}

Portfólio: {portfolio_number}
Período: Q{quarter}/{year}

BASE DE CÁLCULO: CHF {basis:,.2f}
TAXA APLICADA: {rate:.2f}% a.a.

VALOR COBRADO:
- CHF {amount_chf:,.2f}
- EUR {amount_eur:,.2f}
"""

            # Adicionar contexto se for período de perdas
            if year in [2008, 2009, 2010]:
                content += "\n⚠️ PERÍODO DE CRISE: Taxa cobrada durante a crise financeira global"

            ref_date = None
            try:
                stmt = fee.get("statement_period", {})
                if stmt.get("end"):
                    ref_date = datetime.strptime(stmt["end"], "%Y-%m-%d").date()
            except:
                pass

            chunks.append(FinancialFactChunk(
                chunk_id=create_chunk_id("facts", "fee", f"{portfolio_number}_{period}"),
                chunk_type=FactsChunkType.FEES,
                content=content,
                source_document=source_doc,
                portfolio_number=portfolio_number,
                portfolio_type="01",
                reference_date=ref_date,
                year=year,
                quarter=f"Q{quarter}" if quarter else None,
                fee_amount_chf=amount_chf,
                fee_amount_eur=amount_eur,
                fee_rate_pct=rate,
                relevance="medium"
            ))

        return chunks

    def _create_rate_evolution_chunk(
        self, data: Dict, portfolio_number: str, source_doc: str
    ) -> Optional[FinancialFactChunk]:
        """Cria chunk de evolução das taxas"""
        rate_evolution = data.get("fee_rate_evolution", [])

        if not rate_evolution:
            return None

        content = f"""EVOLUÇÃO DAS TAXAS DE GESTÃO

Portfólio: {portfolio_number}

"""
        for evolution in rate_evolution:
            period = evolution.get("period", "")
            rate = evolution.get("rate_pct", 0)
            note = evolution.get("note", "")
            content += f"- {period}: {rate:.2f}% a.a."
            if note:
                content += f" ({note})"
            content += "\n"

        content += """
OBSERVAÇÃO: As taxas continuaram sendo cobradas mesmo quando:
- O portfólio estava em queda
- Fundos estavam congelados (Global Property Fund)
- O cliente não tinha como resgatar
"""

        return FinancialFactChunk(
            chunk_id=create_chunk_id("facts", "rate_evolution", portfolio_number),
            chunk_type=FactsChunkType.FEES,
            content=content,
            source_document=source_doc,
            portfolio_number=portfolio_number,
            portfolio_type="01",
            relevance="high"
        )
