"""
Processador de Timeline de Eventos.
Converte JSON de timeline em chunks para o RAG.
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.models.chunks import (
    ContextChunk,
    ClientTimelineChunk,
    UBSScandalChunk,
    ContextChunkType,
    ClientChunkType,
    create_chunk_id
)


class TimelineProcessor:
    """Processa Timeline JSON e gera chunks"""

    CATEGORY_MAPPING = {
        "global": ContextChunkType.GLOBAL_EVENT,
        "ubs_corporate": ContextChunkType.UBS_CORPORATE,
        "ubs_scandal": ContextChunkType.UBS_SCANDAL,
        "ubs_fund": ContextChunkType.UBS_CORPORATE,
        "market_event": ContextChunkType.MARKET_EVENT,
        "client": None  # Tratado separadamente
    }

    def __init__(self, timeline_dir: str = "data/raw/timeline"):
        self.timeline_dir = Path(timeline_dir)

    def process_all(self) -> Dict[str, List]:
        """Processa todos os arquivos de timeline"""
        context_chunks = []
        client_chunks = []

        for json_file in self.timeline_dir.glob("*.json"):
            try:
                results = self.process_timeline_file(json_file)
                context_chunks.extend(results.get("context", []))
                client_chunks.extend(results.get("client", []))
                print(f"  ✓ {json_file.name}: {len(results.get('context', []))} context + {len(results.get('client', []))} client")
            except Exception as e:
                print(f"  ✗ {json_file.name}: {e}")

        return {
            "context": context_chunks,
            "client": client_chunks
        }

    def process_timeline_file(self, json_path: Path) -> Dict[str, List]:
        """Processa um arquivo de timeline"""
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        context_chunks = []
        client_chunks = []

        for event in data.get("timeline", []):
            category = event.get("category", "")

            if category == "client":
                chunk = self._create_client_chunk(event)
                if chunk:
                    client_chunks.append(chunk)
            else:
                chunk = self._create_context_chunk(event)
                if chunk:
                    context_chunks.append(chunk)

        return {
            "context": context_chunks,
            "client": client_chunks
        }

    def _parse_date(self, date_str: str) -> tuple:
        """Parse de data com diferentes formatos"""
        if not date_str:
            return None, "day"

        try:
            if len(date_str) == 7:  # "2008-12"
                event_date = datetime.strptime(date_str + "-01", "%Y-%m-%d").date()
                precision = "month"
            elif len(date_str) == 4:  # "2008"
                event_date = datetime.strptime(date_str + "-01-01", "%Y-%m-%d").date()
                precision = "year"
            else:  # "2008-12-15"
                event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                precision = "day"
            return event_date, precision
        except:
            return None, "day"

    def _create_context_chunk(self, event: Dict) -> Optional[ContextChunk]:
        """Cria chunk de contexto histórico"""
        category = event.get("category", "")
        date_str = event.get("date", "")

        event_date, precision = self._parse_date(date_str)
        if not event_date:
            return None

        title = event.get("title", "")
        description = event.get("description", "")
        impact = event.get("impact", "")
        relevance = event.get("relevance", "context")
        source = event.get("source", "")
        source_url = event.get("source_url")

        # Determinar tipo de chunk
        chunk_type = self.CATEGORY_MAPPING.get(category, ContextChunkType.GLOBAL_EVENT)

        # Mapear relevance para relevance_to_client
        relevance_mapping = {
            "critical": "direct",
            "high": "direct",
            "pattern": "indirect",
            "context": "context"
        }
        relevance_to_client = relevance_mapping.get(relevance, "context")

        # Construir conteúdo
        content = f"""EVENTO: {title}
Data: {date_str}
Categoria: {category.upper().replace('_', ' ')}

{description}

IMPACTO NO CASO: {impact}

RELEVÂNCIA: {relevance}
"""
        if source:
            content += f"\nFONTE: {source}"
        if source_url:
            content += f"\nURL: {source_url}"

        # Se for escândalo UBS, usar classe específica
        if category == "ubs_scandal":
            return UBSScandalChunk(
                chunk_id=create_chunk_id("context", "scandal", f"{date_str}_{title[:20]}"),
                chunk_type=ContextChunkType.UBS_SCANDAL,
                content=content,
                source_document=source,
                source_url=source_url,
                event_date=event_date,
                event_date_precision=precision,
                event_title=title,
                event_description=description,
                impact_on_case=impact,
                relevance_to_client=relevance_to_client,
                scandal_type=event.get("scandal_type", ""),
                relevance=relevance if relevance in ["critical", "high", "medium", "low"] else "medium"
            )

        return ContextChunk(
            chunk_id=create_chunk_id("context", category, f"{date_str}_{title[:20]}"),
            chunk_type=chunk_type,
            content=content,
            source_document=source,
            source_url=source_url,
            event_date=event_date,
            event_date_precision=precision,
            event_title=title,
            event_description=description,
            impact_on_case=impact,
            relevance_to_client=relevance_to_client,
            relevance=relevance if relevance in ["critical", "high", "medium", "low"] else "medium"
        )

    def _create_client_chunk(self, event: Dict) -> Optional[ClientTimelineChunk]:
        """Cria chunk de timeline do cliente"""
        date_str = event.get("date", "")

        event_date, _ = self._parse_date(date_str)
        if not event_date:
            return None

        title = event.get("title", "")
        description = event.get("description", "")
        impact = event.get("impact", "")
        source = event.get("source", "")
        source_doc = event.get("source_document", source)
        relevance = event.get("relevance", "high")

        # Extrair valores se disponíveis
        value_before = event.get("value_before")
        value_after = event.get("value_after")
        change_pct = event.get("change_pct")

        content = f"""EVENTO DO CLIENTE: {title}
Data: {date_str}

{description}

IMPACTO: {impact}

"""
        if value_before and value_after:
            content += f"VALOR ANTES: EUR {value_before:,.2f}\n"
            content += f"VALOR DEPOIS: EUR {value_after:,.2f}\n"
            if change_pct:
                content += f"VARIAÇÃO: {change_pct:+.2f}%\n"

        content += f"\nFONTE: {source_doc}"

        # Determinar decision_maker
        decision_maker = "ubs"  # Default
        if "cliente" in description.lower() or "client" in description.lower():
            decision_maker = "client"
        elif "mercado" in description.lower() or "market" in description.lower():
            decision_maker = "market"

        return ClientTimelineChunk(
            chunk_id=create_chunk_id("client", "event", f"{date_str}_{title[:20]}"),
            chunk_type=ClientChunkType.CLIENT_EVENT,
            content=content,
            source_document=source_doc,
            event_date=event_date,
            event_title=title,
            event_description=description,
            value_before=value_before,
            value_after=value_after,
            change_pct=change_pct,
            decision_maker=decision_maker,
            relevance=relevance if relevance in ["critical", "high", "medium", "low"] else "high"
        )
