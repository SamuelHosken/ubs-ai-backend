"""
Modelos Pydantic para chunks do sistema RAG Forense.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import date
from enum import Enum
import hashlib


class ChunkCategory(str, Enum):
    """Categorias principais de chunks (correspondem às collections)"""
    # PRIORIDADE MÁXIMA - Fonte principal de conhecimento
    COMPLETE_ANALYSIS = "complete_analysis"

    # Fontes secundárias - dados específicos
    FACTS = "portfolio_facts"
    FORENSIC = "forensic_analysis"
    CONTEXT = "historical_context"
    CLIENT = "client_timeline"
    UBS_OFFICIAL = "ubs_official_docs"


class FactsChunkType(str, Enum):
    """Tipos de chunks para fatos financeiros"""
    OVERVIEW = "overview"
    ALLOCATION = "allocation"
    PERFORMANCE = "performance"
    POSITIONS = "positions"
    TRANSACTIONS = "transactions"
    FEES = "fees"
    FEES_SUMMARY = "fees_summary"


class ForensicChunkType(str, Enum):
    """Tipos de chunks para análise forense"""
    VIOLATION = "violation"
    EVIDENCE = "evidence"
    ANALYSIS = "analysis"
    CONCLUSION = "conclusion"
    RECOMMENDATION = "recommendation"


class CompleteAnalysisChunkType(str, Enum):
    """Tipos de chunks para análise completa (fonte principal)"""
    EXECUTIVE_SUMMARY = "executive_summary"
    SECTION = "section"
    CONCLUSION = "conclusion"
    FULL_NARRATIVE = "full_narrative"


class ContextChunkType(str, Enum):
    """Tipos de chunks para contexto histórico"""
    GLOBAL_EVENT = "global_event"
    UBS_SCANDAL = "ubs_scandal"
    UBS_CORPORATE = "ubs_corporate"
    MARKET_EVENT = "market_event"


class ClientChunkType(str, Enum):
    """Tipos de chunks para timeline do cliente"""
    CLIENT_EVENT = "client_event"
    LOSS_ANALYSIS = "loss_analysis"
    SUITABILITY_VIOLATION = "suitability_violation"


class UBSOfficialChunkType(str, Enum):
    """Tipos de chunks para documentos oficiais UBS"""
    CODE_OF_CONDUCT = "code_of_conduct"
    INVESTOR_PROFILE = "investor_profile"
    PRODUCT_REQUIREMENTS = "product_requirements"
    RISK_DISCLOSURE = "risk_disclosure"
    INTERNAL_REPORT = "internal_report"
    REGULATORY_FILING = "regulatory_filing"


# ============================================================
# CHUNKS BASE
# ============================================================

class BaseChunk(BaseModel):
    """Base para todos os chunks"""
    chunk_id: str
    content: str
    content_pt: Optional[str] = None

    # Fonte
    source_document: str
    source_page: Optional[int] = None
    source_url: Optional[str] = None

    # Metadados
    language: str = "en"
    relevance: Literal["critical", "high", "medium", "low"] = "medium"


# ============================================================
# CHUNKS DE ANÁLISE COMPLETA (PRIORIDADE MÁXIMA)
# ============================================================

class CompleteAnalysisChunk(BaseChunk):
    """Chunk de análise completa - FONTE PRINCIPAL de conhecimento"""
    category: Literal["complete_analysis"] = "complete_analysis"
    chunk_type: CompleteAnalysisChunkType

    # Identificação
    portfolio_number: str
    section_number: Optional[int] = None
    section_title: Optional[str] = None

    # Conteúdo estruturado
    is_executive_summary: bool = False
    is_conclusion: bool = False

    # Números-chave extraídos
    key_figures: Optional[Dict[str, Any]] = None

    # Responsabilidade
    responsibility_attribution: Optional[Dict[str, str]] = None

    # Violações identificadas
    violations_mentioned: List[str] = Field(default_factory=list)


# ============================================================
# CHUNKS DE FATOS FINANCEIROS
# ============================================================

class FinancialFactChunk(BaseChunk):
    """Chunk de dados financeiros (Statements/Fees)"""
    category: Literal["portfolio_facts"] = "portfolio_facts"
    chunk_type: FactsChunkType

    # Identificação
    portfolio_number: str
    portfolio_type: Literal["01", "02"]
    reference_date: Optional[date] = None
    year: Optional[int] = None
    quarter: Optional[str] = None

    # Valores numéricos
    net_assets_eur: Optional[float] = None
    net_assets_chf: Optional[float] = None
    performance_pct: Optional[float] = None

    # Para chunks de alocação
    asset_class: Optional[str] = None
    allocation_pct: Optional[float] = None

    # Para chunks de fees
    fee_amount_eur: Optional[float] = None
    fee_amount_chf: Optional[float] = None
    fee_rate_pct: Optional[float] = None


class FeesChunk(BaseChunk):
    """Chunk específico para taxas"""
    category: Literal["portfolio_facts"] = "portfolio_facts"
    chunk_type: Literal["fees", "fees_summary"] = "fees"

    portfolio_number: str
    period_start: Optional[date] = None
    period_end: Optional[date] = None

    # Valores
    total_fees_eur: Optional[float] = None
    total_fees_chf: Optional[float] = None
    avg_rate_pct: Optional[float] = None
    num_periods: Optional[int] = None


# ============================================================
# CHUNKS DE ANÁLISE FORENSE
# ============================================================

class ForensicChunk(BaseChunk):
    """Chunk de análise forense/jurídica"""
    category: Literal["forensic_analysis"] = "forensic_analysis"
    chunk_type: ForensicChunkType

    # Identificação
    portfolio_affected: Optional[str] = None
    violation_type: Optional[str] = None

    # Severidade
    severity: Literal["critical", "grave", "moderate", "minor"] = "moderate"

    # Evidências linkadas
    evidence_refs: List[Dict[str, Any]] = Field(default_factory=list)

    # Conclusão
    conclusion: Optional[str] = None
    responsibility_attribution: Optional[str] = None


class ViolationChunk(ForensicChunk):
    """Chunk específico para violações identificadas"""
    chunk_type: Literal[ForensicChunkType.VIOLATION] = ForensicChunkType.VIOLATION

    violation_category: Optional[str] = None
    regulatory_basis: Optional[str] = None

    # Danos
    financial_impact_eur: Optional[float] = None
    percentage_loss: Optional[float] = None

    # Período da violação
    violation_start: Optional[date] = None
    violation_end: Optional[date] = None


# ============================================================
# CHUNKS DE CONTEXTO HISTÓRICO
# ============================================================

class ContextChunk(BaseChunk):
    """Chunk de contexto histórico (eventos globais/UBS)"""
    category: Literal["historical_context"] = "historical_context"
    chunk_type: ContextChunkType

    # Temporal
    event_date: Optional[date] = None
    event_date_precision: Literal["day", "month", "year"] = "day"

    # Descrição
    event_title: str
    event_description: str

    # Impacto no caso
    impact_on_case: Optional[str] = None
    relevance_to_client: Literal["direct", "indirect", "context"] = "context"

    # Para escândalos UBS
    fine_amount_usd: Optional[float] = None
    regulatory_body: Optional[str] = None


class UBSScandalChunk(ContextChunk):
    """Chunk específico para escândalos da UBS"""
    chunk_type: Literal[ContextChunkType.UBS_SCANDAL] = ContextChunkType.UBS_SCANDAL

    scandal_type: Optional[str] = None
    settlement_amount: Optional[float] = None
    criminal_charges: bool = False
    executives_affected: List[str] = Field(default_factory=list)


# ============================================================
# CHUNKS DE TIMELINE DO CLIENTE
# ============================================================

class ClientTimelineChunk(BaseChunk):
    """Chunk de eventos específicos do cliente"""
    category: Literal["client_timeline"] = "client_timeline"
    chunk_type: ClientChunkType

    # Temporal
    event_date: Optional[date] = None

    # Identificação
    portfolio_number: Optional[str] = None

    # Evento
    event_title: str
    event_description: str

    # Impacto financeiro
    value_before: Optional[float] = None
    value_after: Optional[float] = None
    change_pct: Optional[float] = None

    # Atribuição de responsabilidade
    decision_maker: Literal["client", "ubs", "market", "regulatory"] = "ubs"
    client_had_choice: bool = False


# ============================================================
# CHUNKS DE DOCUMENTOS OFICIAIS UBS
# ============================================================

class UBSOfficialDocChunk(BaseChunk):
    """Chunk de documentos oficiais da UBS"""
    category: Literal["ubs_official_docs"] = "ubs_official_docs"
    chunk_type: UBSOfficialChunkType

    # Documento
    document_title: str
    document_date: Optional[date] = None
    document_version: Optional[str] = None

    # Classificação
    document_type: str = "official"
    is_public: bool = True

    # Seção específica
    section_title: Optional[str] = None
    section_number: Optional[str] = None

    # Relevância para violações
    relevant_to_violations: List[str] = Field(default_factory=list)

    # Quote exata para citação
    exact_quote: Optional[str] = None
    quote_page: Optional[int] = None


# ============================================================
# HELPERS
# ============================================================

def get_collection_for_category(category: ChunkCategory) -> str:
    """Retorna o nome da collection no ChromaDB para uma categoria"""
    return category.value


def create_chunk_id(category: str, chunk_type: str, identifier: str) -> str:
    """Cria ID único para um chunk"""
    import uuid
    # Adicionar componente único para garantir unicidade
    raw = f"{category}_{chunk_type}_{identifier}_{uuid.uuid4().hex[:8]}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]
