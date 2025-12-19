"""
Processador de Statements of Assets extraídos.
Converte JSONs em chunks para o RAG.
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.models.chunks import (
    FinancialFactChunk,
    FactsChunkType,
    create_chunk_id
)


class StatementsProcessor:
    """Processa JSONs de Statements e gera chunks"""

    def __init__(self, statements_dir: str = "data/raw/statements"):
        self.statements_dir = Path(statements_dir)

    def process_all(self) -> List[FinancialFactChunk]:
        """Processa todos os statements"""
        all_chunks = []

        for json_file in sorted(self.statements_dir.glob("*.json")):
            try:
                chunks = self.process_statement(json_file)
                all_chunks.extend(chunks)
                print(f"  ✓ {json_file.name}: {len(chunks)} chunks")
            except Exception as e:
                print(f"  ✗ {json_file.name}: {e}")

        return all_chunks

    def process_statement(self, json_path: Path) -> List[FinancialFactChunk]:
        """Processa um único statement JSON"""
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        chunks = []

        # Extrair metadados base
        metadata = data.get("metadata", {})
        doc_info = data.get("_document_info", {})

        portfolio_number = metadata.get("portfolio_number", "")
        portfolio_type = doc_info.get("portfolio_type", "01")
        if not portfolio_type:
            portfolio_type = "02" if "-02" in portfolio_number else "01"

        ref_date_str = metadata.get("reference_date", "")
        ref_date = None
        year = None
        quarter = None

        if ref_date_str:
            try:
                ref_date = datetime.strptime(ref_date_str, "%Y-%m-%d").date()
                year = ref_date.year
                quarter = f"Q{(ref_date.month - 1) // 3 + 1}"
            except:
                pass

        source_doc = json_path.stem

        # 1. CHUNK: Overview
        overview_chunk = self._create_overview_chunk(
            data, portfolio_number, portfolio_type, ref_date, year, quarter, source_doc
        )
        if overview_chunk:
            chunks.append(overview_chunk)

        # 2. CHUNK: Allocation
        allocation_chunks = self._create_allocation_chunks(
            data, portfolio_number, portfolio_type, ref_date, year, quarter, source_doc
        )
        chunks.extend(allocation_chunks)

        # 3. CHUNK: Performance
        performance_chunk = self._create_performance_chunk(
            data, portfolio_number, portfolio_type, ref_date, year, quarter, source_doc
        )
        if performance_chunk:
            chunks.append(performance_chunk)

        # 4. CHUNKS: Positions (top 10 por valor)
        position_chunks = self._create_position_chunks(
            data, portfolio_number, portfolio_type, ref_date, year, quarter, source_doc
        )
        chunks.extend(position_chunks)

        # 5. CHUNKS: Cash Flows (inflows/outflows) - CRÍTICO PARA ANÁLISE
        cashflow_chunks = self._create_cashflow_chunks(
            data, portfolio_number, portfolio_type, ref_date, year, quarter, source_doc
        )
        chunks.extend(cashflow_chunks)

        # 6. CHUNKS: Currency Allocation (exposição por moeda)
        currency_chunks = self._create_currency_allocation_chunks(
            data, portfolio_number, portfolio_type, ref_date, year, quarter, source_doc
        )
        chunks.extend(currency_chunks)

        # 7. CHUNKS: Transactions (compras/vendas) - IMPORTANTE para auditoria
        transaction_chunks = self._create_transaction_chunks(
            data, portfolio_number, portfolio_type, ref_date, year, quarter, source_doc
        )
        chunks.extend(transaction_chunks)

        # 8. CHUNKS: Market Commentary (opinião do UBS) - CRÍTICO para responsabilidade
        commentary_chunks = self._create_market_commentary_chunks(
            data, portfolio_number, portfolio_type, ref_date, year, quarter, source_doc
        )
        chunks.extend(commentary_chunks)

        # 9. CHUNKS: Fee Disclosure (taxas cobradas) - CRÍTICO para perdas
        fee_chunks = self._create_fee_disclosure_chunks(
            data, portfolio_number, portfolio_type, ref_date, year, quarter, source_doc
        )
        chunks.extend(fee_chunks)

        # 10. CHUNKS: Historical Context (pico a final) - CRÍTICO para danos
        historical_chunks = self._create_historical_context_chunks(
            data, portfolio_number, portfolio_type, ref_date, year, quarter, source_doc
        )
        chunks.extend(historical_chunks)

        # 11. CHUNKS: Notes (notas dos documentos)
        notes_chunks = self._create_notes_chunks(
            data, portfolio_number, portfolio_type, ref_date, year, quarter, source_doc
        )
        chunks.extend(notes_chunks)

        return chunks

    def _create_overview_chunk(
        self, data: Dict, portfolio_number: str, portfolio_type: str,
        ref_date, year: int, quarter: str, source_doc: str
    ) -> Optional[FinancialFactChunk]:
        """Cria chunk de overview"""
        totals = data.get("totals", {})
        metadata = data.get("metadata", {})
        performance = data.get("performance", {})

        net_assets = totals.get("net_assets_eur") or totals.get("net_assets")
        if net_assets is None:
            return None

        strategy = metadata.get("investment_strategy", "")
        program = metadata.get("program", "")
        ytd_pct = performance.get("ytd_pct")

        # Construir texto rico para embedding
        portfolio_type_desc = "Diversificado (Yield)" if portfolio_type == "01" else "100% Real Estate (Mandate RE)"

        content = f"""RESUMO DO PORTFÓLIO

Portfólio: {portfolio_number}
Tipo: {portfolio_type_desc}
Data de Referência: {ref_date}
Ano: {year} | Trimestre: {quarter}

PROGRAMA: {program}
ESTRATÉGIA: {strategy}

PATRIMÔNIO LÍQUIDO: EUR {net_assets:,.2f}
"""
        if ytd_pct is not None:
            content += f"\nPERFORMANCE YTD: {ytd_pct:+.2f}%"

        return FinancialFactChunk(
            chunk_id=create_chunk_id("facts", "overview", f"{portfolio_number}_{ref_date}"),
            chunk_type=FactsChunkType.OVERVIEW,
            content=content,
            source_document=source_doc,
            portfolio_number=portfolio_number,
            portfolio_type=portfolio_type,
            reference_date=ref_date,
            year=year,
            quarter=quarter,
            net_assets_eur=float(net_assets) if net_assets else None,
            performance_pct=float(ytd_pct) if ytd_pct else None,
            relevance="critical" if portfolio_type == "02" else "high"
        )

    def _create_allocation_chunks(
        self, data: Dict, portfolio_number: str, portfolio_type: str,
        ref_date, year: int, quarter: str, source_doc: str
    ) -> List[FinancialFactChunk]:
        """Cria chunks de alocação"""
        chunks = []
        allocations = data.get("asset_allocation", [])

        if not allocations or not isinstance(allocations, list):
            return chunks

        # Filtrar apenas dicts válidos
        allocations = [a for a in allocations if isinstance(a, dict)]

        if not allocations:
            return chunks

        # Chunk consolidado de alocação
        allocation_text = f"""ALOCAÇÃO DO PORTFÓLIO {portfolio_number}
Data: {ref_date}

"""
        for alloc in allocations:
            asset_class = alloc.get("asset_class", "")
            market_value = alloc.get("market_value", 0)
            pct = alloc.get("percentage", 0)
            allocation_text += f"- {asset_class}: EUR {market_value:,.2f} ({pct:.2f}%)\n"

        chunks.append(FinancialFactChunk(
            chunk_id=create_chunk_id("facts", "allocation", f"{portfolio_number}_{ref_date}"),
            chunk_type=FactsChunkType.ALLOCATION,
            content=allocation_text,
            source_document=source_doc,
            portfolio_number=portfolio_number,
            portfolio_type=portfolio_type,
            reference_date=ref_date,
            year=year,
            quarter=quarter,
            relevance="high"
        ))

        return chunks

    def _create_performance_chunk(
        self, data: Dict, portfolio_number: str, portfolio_type: str,
        ref_date, year: int, quarter: str, source_doc: str
    ) -> Optional[FinancialFactChunk]:
        """Cria chunk de performance"""
        performance = data.get("performance", {})

        if not performance:
            return None

        ytd = performance.get("ytd_pct")
        cumulative = performance.get("cumulative_pct") or performance.get("since_inception_pct")
        history = performance.get("annual_history", [])
        monthly = performance.get("monthly_returns", [])

        content = f"""PERFORMANCE DO PORTFÓLIO {portfolio_number}
Data de Referência: {ref_date}

"""
        if ytd is not None:
            content += f"Performance YTD: {ytd:+.2f}%\n"
        if cumulative is not None:
            content += f"Performance Acumulada: {cumulative:+.2f}%\n"

        if history:
            content += "\nHISTÓRICO ANUAL:\n"
            for h in history:
                y = h.get("year")
                p = h.get("performance_pct")
                if y and p is not None:
                    content += f"  {y}: {p:+.2f}%\n"

        if monthly:
            content += "\nRETORNOS MENSAIS:\n"
            for m in monthly:
                month = m.get("month")
                ret = m.get("return_pct")
                if month and ret is not None:
                    content += f"  {month}: {ret:+.2f}%\n"

        return FinancialFactChunk(
            chunk_id=create_chunk_id("facts", "performance", f"{portfolio_number}_{ref_date}"),
            chunk_type=FactsChunkType.PERFORMANCE,
            content=content,
            source_document=source_doc,
            portfolio_number=portfolio_number,
            portfolio_type=portfolio_type,
            reference_date=ref_date,
            year=year,
            quarter=quarter,
            performance_pct=float(ytd) if ytd else None,
            relevance="critical" if portfolio_type == "02" else "high"
        )

    def _create_position_chunks(
        self, data: Dict, portfolio_number: str, portfolio_type: str,
        ref_date, year: int, quarter: str, source_doc: str,
        max_positions: int = 10
    ) -> List[FinancialFactChunk]:
        """Cria chunks para posições individuais (top N)"""
        chunks = []
        positions = data.get("positions", [])

        if not positions or not isinstance(positions, list):
            return chunks

        # Filtrar apenas dicts válidos
        valid_positions = [p for p in positions if isinstance(p, dict)]

        if not valid_positions:
            return chunks

        # Ordenar por valor e pegar top N
        sorted_positions = sorted(
            valid_positions,
            key=lambda x: abs(x.get("market_value", 0) or 0),
            reverse=True
        )[:max_positions]

        for pos in sorted_positions:
            if not isinstance(pos, dict):
                continue

            name = pos.get("name", "Unknown")
            category = pos.get("category", "")
            value = pos.get("market_value", 0)
            pct = pos.get("percentage", 0) or pos.get("performance_pct", 0)
            isin = pos.get("isin", "")

            if not value or abs(value) < 100:
                continue

            content = f"""POSIÇÃO: {name}
Portfólio: {portfolio_number}
Data: {ref_date}

Categoria: {category}
ISIN: {isin or 'N/A'}
Valor de Mercado: EUR {value:,.2f}
Percentual do Portfólio: {pct:.2f}%
"""

            # Destacar posições do Global Property Fund
            if "global property" in name.lower() or "mandate re" in name.lower():
                content += "\n⚠️ ATENÇÃO: Esta é a posição do UBS Global Property Fund"

            chunks.append(FinancialFactChunk(
                chunk_id=create_chunk_id("facts", "position", f"{portfolio_number}_{ref_date}_{name[:20]}"),
                chunk_type=FactsChunkType.POSITIONS,
                content=content,
                source_document=source_doc,
                portfolio_number=portfolio_number,
                portfolio_type=portfolio_type,
                reference_date=ref_date,
                year=year,
                quarter=quarter,
                asset_class=category,
                net_assets_eur=float(value) if value else None,
                relevance="critical" if "property" in name.lower() else "medium"
            ))

        return chunks

    def _create_cashflow_chunks(
        self, data: Dict, portfolio_number: str, portfolio_type: str,
        ref_date, year: int, quarter: str, source_doc: str
    ) -> List[FinancialFactChunk]:
        """Cria chunks de cash flows (inflows/outflows) - CRÍTICO para análise"""
        chunks = []

        # Buscar todos os cash_flows_YYYY no documento
        for key in data:
            if key.startswith("cash_flows_") or key == "cash_flows":
                cf_data = data[key]
                if not isinstance(cf_data, dict):
                    continue

                cf_year = key.replace("cash_flows_", "") if "_" in key else str(year)

                # Extrair totais
                total_outflows = cf_data.get("total_outflows", 0) or 0
                total_inflows = cf_data.get("total_inflows", 0) or 0
                net_flow = cf_data.get("net_flow", 0) or 0

                # Construir texto descritivo
                content = f"""FLUXO DE CAIXA (CASH FLOW) - PORTFÓLIO {portfolio_number}
Ano: {cf_year}
Tipo de Portfólio: {"Diversificado (01)" if portfolio_type == "01" else "Real Estate (02)"}
Documento de Referência: {source_doc}

=== RESUMO ANUAL ===
RETIRADAS (OUTFLOWS): EUR {abs(total_outflows):,.2f}
APORTES (INFLOWS): EUR {total_inflows:,.2f}
FLUXO LÍQUIDO: EUR {net_flow:,.2f}

"""
                # Adicionar detalhes por trimestre se disponível
                for q_key in ["q1", "q2", "q3", "q4"]:
                    q_data = cf_data.get(q_key, {})
                    if not q_data:
                        continue

                    transactions = q_data.get("transactions", [])
                    subtotal = q_data.get("subtotal", 0) or 0

                    if transactions or subtotal:
                        q_name = q_key.upper()
                        content += f"\n{q_name} - Subtotal: EUR {subtotal:,.2f}\n"

                        if isinstance(transactions, list):
                            for t in transactions[:5]:  # Limitar transações
                                if isinstance(t, dict):
                                    t_date = t.get("date", "")
                                    t_amount = t.get("amount", 0) or t.get("amount_eur", 0) or 0
                                    t_type = t.get("type", "")
                                    t_currency = t.get("currency", "EUR")
                                    content += f"  - {t_date}: EUR {t_amount:,.2f} ({t_type}) {t_currency}\n"

                # Criar chunk
                chunks.append(FinancialFactChunk(
                    chunk_id=create_chunk_id("facts", "cashflow", f"{portfolio_number}_{cf_year}"),
                    chunk_type=FactsChunkType.TRANSACTIONS,
                    content=content,
                    source_document=source_doc,
                    portfolio_number=portfolio_number,
                    portfolio_type=portfolio_type,
                    reference_date=ref_date,
                    year=int(cf_year) if cf_year.isdigit() else year,
                    quarter=quarter,
                    net_assets_eur=float(net_flow) if net_flow else None,
                    relevance="critical"  # Cash flows são sempre críticos para o caso
                ))

        # Também buscar "balance" que pode ter inflows/outflows
        balance = data.get("balance", {})
        if balance and isinstance(balance, dict):
            inflows = balance.get("inflows", [])
            outflows = balance.get("outflows", [])

            if inflows or outflows:
                content = f"""MOVIMENTAÇÕES DO PORTFÓLIO {portfolio_number}
Data de Referência: {ref_date}
Tipo de Portfólio: {"Diversificado (01)" if portfolio_type == "01" else "Real Estate (02)"}

"""
                if outflows:
                    content += "=== RETIRADAS (OUTFLOWS) ===\n"
                    for out in outflows:
                        if isinstance(out, dict):
                            desc = out.get("description", "")
                            amount = out.get("amount", 0)
                            content += f"- {desc}: EUR {amount:,.2f}\n"

                if inflows:
                    content += "\n=== APORTES (INFLOWS) ===\n"
                    for inf in inflows:
                        if isinstance(inf, dict):
                            desc = inf.get("description", "")
                            amount = inf.get("amount", 0)
                            content += f"- {desc}: EUR {amount:,.2f}\n"

                chunks.append(FinancialFactChunk(
                    chunk_id=create_chunk_id("facts", "balance", f"{portfolio_number}_{ref_date}"),
                    chunk_type=FactsChunkType.TRANSACTIONS,
                    content=content,
                    source_document=source_doc,
                    portfolio_number=portfolio_number,
                    portfolio_type=portfolio_type,
                    reference_date=ref_date,
                    year=year,
                    quarter=quarter,
                    relevance="critical"
                ))

        return chunks

    def _create_currency_allocation_chunks(
        self, data: Dict, portfolio_number: str, portfolio_type: str,
        ref_date, year: int, quarter: str, source_doc: str
    ) -> List[FinancialFactChunk]:
        """Cria chunks de alocação por moeda - exposição cambial"""
        chunks = []
        currency_alloc = data.get("currency_allocation", [])

        if not currency_alloc or not isinstance(currency_alloc, list):
            return chunks

        valid_allocs = [c for c in currency_alloc if isinstance(c, dict)]
        if not valid_allocs:
            return chunks

        content = f"""ALOCAÇÃO POR MOEDA - PORTFÓLIO {portfolio_number}
Data de Referência: {ref_date}
Tipo de Portfólio: {"Diversificado (01)" if portfolio_type == "01" else "Real Estate (02)"}

=== EXPOSIÇÃO CAMBIAL ===
"""
        for alloc in valid_allocs:
            currency = alloc.get("currency", "N/A")
            value = alloc.get("market_value", 0) or 0
            pct = alloc.get("percentage", 0) or 0
            content += f"- {currency}: EUR {value:,.2f} ({pct:.2f}%)\n"

        chunks.append(FinancialFactChunk(
            chunk_id=create_chunk_id("facts", "currency", f"{portfolio_number}_{ref_date}"),
            chunk_type=FactsChunkType.ALLOCATION,
            content=content,
            source_document=source_doc,
            portfolio_number=portfolio_number,
            portfolio_type=portfolio_type,
            reference_date=ref_date,
            year=year,
            quarter=quarter,
            relevance="medium"
        ))

        return chunks

    def _create_transaction_chunks(
        self, data: Dict, portfolio_number: str, portfolio_type: str,
        ref_date, year: int, quarter: str, source_doc: str
    ) -> List[FinancialFactChunk]:
        """Cria chunks de transações (compras/vendas) - auditoria de operações"""
        chunks = []
        transactions = data.get("transactions", [])

        if not transactions or not isinstance(transactions, list):
            # Tentar balance_statement
            balance_stmt = data.get("balance_statement", {})
            if balance_stmt:
                transactions = balance_stmt.get("transactions", [])

        if not transactions:
            return chunks

        valid_trans = [t for t in transactions if isinstance(t, dict)]
        if not valid_trans:
            return chunks

        # Agrupar transações por tipo
        purchases = [t for t in valid_trans if t.get("type", "").lower() in ["purchase", "buy", "compra"]]
        sales = [t for t in valid_trans if t.get("type", "").lower() in ["sale", "sell", "venda"]]
        others = [t for t in valid_trans if t not in purchases and t not in sales]

        content = f"""TRANSAÇÕES DO PORTFÓLIO {portfolio_number}
Data de Referência: {ref_date}
Total de Transações: {len(valid_trans)}

"""
        if purchases:
            content += f"=== COMPRAS ({len(purchases)} operações) ===\n"
            total_purchases = 0
            for t in purchases[:10]:  # Limitar a 10
                date = t.get("date", "")
                security = t.get("security_name", "")[:50]
                value = abs(t.get("net_value", 0) or t.get("gross_value", 0) or 0)
                currency = t.get("currency", "EUR")
                total_purchases += value
                content += f"- {date}: {security} = {currency} {value:,.2f}\n"
            content += f"TOTAL COMPRAS: EUR {total_purchases:,.2f}\n\n"

        if sales:
            content += f"=== VENDAS ({len(sales)} operações) ===\n"
            total_sales = 0
            for t in sales[:10]:
                date = t.get("date", "")
                security = t.get("security_name", "")[:50]
                value = abs(t.get("net_value", 0) or t.get("gross_value", 0) or 0)
                currency = t.get("currency", "EUR")
                total_sales += value
                content += f"- {date}: {security} = {currency} {value:,.2f}\n"
            content += f"TOTAL VENDAS: EUR {total_sales:,.2f}\n\n"

        if others:
            content += f"=== OUTRAS OPERAÇÕES ({len(others)}) ===\n"
            for t in others[:5]:
                date = t.get("date", "")
                desc = t.get("description", "") or t.get("security_name", "")
                amount = t.get("amount", 0) or t.get("net_value", 0) or 0
                content += f"- {date}: {desc[:50]} = EUR {amount:,.2f}\n"

        chunks.append(FinancialFactChunk(
            chunk_id=create_chunk_id("facts", "transactions", f"{portfolio_number}_{ref_date}"),
            chunk_type=FactsChunkType.TRANSACTIONS,
            content=content,
            source_document=source_doc,
            portfolio_number=portfolio_number,
            portfolio_type=portfolio_type,
            reference_date=ref_date,
            year=year,
            quarter=quarter,
            relevance="high"
        ))

        return chunks

    def _create_market_commentary_chunks(
        self, data: Dict, portfolio_number: str, portfolio_type: str,
        ref_date, year: int, quarter: str, source_doc: str
    ) -> List[FinancialFactChunk]:
        """Cria chunks de comentário de mercado do UBS - CRÍTICO para responsabilidade"""
        chunks = []
        commentary = data.get("market_commentary", {})

        if not commentary or not isinstance(commentary, dict):
            return chunks

        content = f"""⚠️ COMENTÁRIO DE MERCADO DO UBS - PORTFÓLIO {portfolio_number}
Data: {ref_date}
Documento: {source_doc}

IMPORTANTE: Este é o que o UBS SABIA e COMUNICOU ao cliente na época.

"""
        # Economia e Política
        econ = commentary.get("economy_and_politics", {})
        if econ:
            content += "=== VISÃO ECONÔMICA DO UBS ===\n"
            if isinstance(econ, dict):
                for region, text in econ.items():
                    content += f"\n[{region.upper()}]\n{text}\n"
            else:
                content += f"{econ}\n"
            content += "\n"

        # Outlook por classe de ativos
        outlook = commentary.get("asset_class_outlook", {})
        if outlook:
            content += "=== PERSPECTIVAS POR CLASSE DE ATIVOS (UBS) ===\n"
            if isinstance(outlook, dict):
                for asset_class, text in outlook.items():
                    content += f"\n[{asset_class.upper()}]\n{text}\n"
            else:
                content += f"{outlook}\n"

        chunks.append(FinancialFactChunk(
            chunk_id=create_chunk_id("facts", "ubs_commentary", f"{portfolio_number}_{ref_date}"),
            chunk_type=FactsChunkType.OVERVIEW,
            content=content,
            source_document=source_doc,
            portfolio_number=portfolio_number,
            portfolio_type=portfolio_type,
            reference_date=ref_date,
            year=year,
            quarter=quarter,
            relevance="critical"  # Crítico para provar o que UBS sabia
        ))

        return chunks

    def _create_fee_disclosure_chunks(
        self, data: Dict, portfolio_number: str, portfolio_type: str,
        ref_date, year: int, quarter: str, source_doc: str
    ) -> List[FinancialFactChunk]:
        """Cria chunks de divulgação de taxas - CRÍTICO para perdas por taxas"""
        chunks = []
        fees = data.get("fee_disclosure", {})

        if not fees or not isinstance(fees, dict):
            return chunks

        content = f"""💰 TAXAS COBRADAS PELO UBS - PORTFÓLIO {portfolio_number}
Data de Referência: {ref_date}
Documento: {source_doc}

=== ESTRUTURA DE TAXAS ===
"""
        for fund_type, fee_rate in fees.items():
            if fund_type == "note":
                content += f"\n⚠️ NOTA: {fee_rate}\n"
            else:
                fund_name = fund_type.replace("_", " ").title()
                content += f"- {fund_name}: {fee_rate}\n"

        content += """
⚠️ ALERTA: Estas taxas impactam diretamente o retorno do cliente.
Taxas elevadas (acima de 1.5% a.a.) são consideradas excessivas para fundos passivos.
"""

        chunks.append(FinancialFactChunk(
            chunk_id=create_chunk_id("facts", "fees", f"{portfolio_number}_{ref_date}"),
            chunk_type=FactsChunkType.OVERVIEW,
            content=content,
            source_document=source_doc,
            portfolio_number=portfolio_number,
            portfolio_type=portfolio_type,
            reference_date=ref_date,
            year=year,
            quarter=quarter,
            relevance="critical"  # Crítico para provar perdas por taxas
        ))

        return chunks

    def _create_historical_context_chunks(
        self, data: Dict, portfolio_number: str, portfolio_type: str,
        ref_date, year: int, quarter: str, source_doc: str
    ) -> List[FinancialFactChunk]:
        """Cria chunks de contexto histórico (pico → final) - CRÍTICO para danos"""
        chunks = []
        hist_context = data.get("_historical_context", {})

        if not hist_context or not isinstance(hist_context, dict):
            return chunks

        peak = hist_context.get("peak_value", {})
        final = hist_context.get("final_value", {})
        decline = hist_context.get("total_decline", {})
        timeline = hist_context.get("timeline_summary", [])

        content = f"""📉 EVOLUÇÃO HISTÓRICA DO PORTFÓLIO {portfolio_number}
Documento: {source_doc}

=== VALOR DE PICO ===
"""
        if peak:
            peak_date = peak.get("date", "N/A")
            peak_chf = peak.get("amount_chf", 0)
            peak_eur = peak.get("amount_eur_equivalent", 0) or peak.get("amount_eur", 0)
            content += f"Data: {peak_date}\n"
            if peak_chf:
                content += f"Valor (CHF): CHF {peak_chf:,.2f}\n"
            if peak_eur:
                content += f"Valor (EUR): EUR {peak_eur:,.2f}\n"

        content += "\n=== VALOR FINAL ===\n"
        if final:
            final_date = final.get("date", "N/A")
            final_eur = final.get("amount_eur", 0)
            content += f"Data: {final_date}\n"
            content += f"Valor (EUR): EUR {final_eur:,.2f}\n"

        content += "\n=== PERDA TOTAL ===\n"
        if decline:
            loss_eur = abs(decline.get("from_peak_eur", 0))
            loss_pct = abs(decline.get("percentage", 0))
            content += f"Perda em EUR: EUR {loss_eur:,.2f}\n"
            content += f"Perda Percentual: {loss_pct:.2f}%\n"

        if timeline:
            content += "\n=== LINHA DO TEMPO ===\n"
            for event in timeline:
                evt_year = event.get("year", "")
                evt_value = event.get("value_eur", 0)
                evt_note = event.get("note", "")
                content += f"- {evt_year}: EUR {evt_value:,.2f} ({evt_note})\n"

        content += """
⚠️ ALERTA: Esta análise mostra a destruição de valor do portfólio ao longo do tempo.
"""

        chunks.append(FinancialFactChunk(
            chunk_id=create_chunk_id("facts", "historical", f"{portfolio_number}_{source_doc}"),
            chunk_type=FactsChunkType.OVERVIEW,
            content=content,
            source_document=source_doc,
            portfolio_number=portfolio_number,
            portfolio_type=portfolio_type,
            reference_date=ref_date,
            year=year,
            quarter=quarter,
            relevance="critical"  # Crítico para provar danos
        ))

        return chunks

    def _create_notes_chunks(
        self, data: Dict, portfolio_number: str, portfolio_type: str,
        ref_date, year: int, quarter: str, source_doc: str
    ) -> List[FinancialFactChunk]:
        """Cria chunks de notas do documento"""
        chunks = []
        notes = data.get("_notes", [])

        if not notes or not isinstance(notes, list):
            return chunks

        valid_notes = [n for n in notes if n and isinstance(n, str)]
        if not valid_notes:
            return chunks

        content = f"""📝 NOTAS DO DOCUMENTO - PORTFÓLIO {portfolio_number}
Data: {ref_date}
Documento: {source_doc}

=== OBSERVAÇÕES IMPORTANTES ===
"""
        for i, note in enumerate(valid_notes, 1):
            content += f"\n{i}. {note}\n"

        chunks.append(FinancialFactChunk(
            chunk_id=create_chunk_id("facts", "notes", f"{portfolio_number}_{ref_date}"),
            chunk_type=FactsChunkType.OVERVIEW,
            content=content,
            source_document=source_doc,
            portfolio_number=portfolio_number,
            portfolio_type=portfolio_type,
            reference_date=ref_date,
            year=year,
            quarter=quarter,
            relevance="medium"
        ))

        return chunks
