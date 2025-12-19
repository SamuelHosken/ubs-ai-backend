"""
Processador de Documentos Oficiais da UBS.
Processa PDFs de documentos oficiais e gera chunks para evidência.
"""
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import PyPDF2

from app.models.chunks import (
    UBSOfficialDocChunk,
    UBSOfficialChunkType,
    create_chunk_id
)


class UBSDocsProcessor:
    """Processa documentos oficiais da UBS"""

    # Mapeamento de arquivos para tipos
    DOC_TYPE_MAPPING = {
        "code_of_conduct": UBSOfficialChunkType.CODE_OF_CONDUCT,
        "code of conduct": UBSOfficialChunkType.CODE_OF_CONDUCT,
        "ethics": UBSOfficialChunkType.CODE_OF_CONDUCT,
        "mifid": UBSOfficialChunkType.INVESTOR_PROFILE,
        "investor_profile": UBSOfficialChunkType.INVESTOR_PROFILE,
        "investor profile": UBSOfficialChunkType.INVESTOR_PROFILE,
        "restructuring": UBSOfficialChunkType.INTERNAL_REPORT,
        "subprime": UBSOfficialChunkType.INTERNAL_REPORT,
        "prospectus": UBSOfficialChunkType.PRODUCT_REQUIREMENTS,
        "annual_report": UBSOfficialChunkType.REGULATORY_FILING,
        "annual report": UBSOfficialChunkType.REGULATORY_FILING,
        "risk": UBSOfficialChunkType.RISK_DISCLOSURE,
    }

    # Seções relevantes para o caso (keywords)
    RELEVANT_SECTIONS = {
        "suitability": [
            "suitability", "suitable", "investor profile", "risk tolerance",
            "investment objectives", "appropriate", "adequação", "perfil"
        ],
        "disclosure": [
            "disclosure", "disclose", "inform", "communicate", "transparency",
            "divulgação", "informar", "comunicar"
        ],
        "fiduciary": [
            "fiduciary", "duty of care", "best interest", "loyalty",
            "fiduciário", "dever", "interesse"
        ],
        "risk_warning": [
            "risk", "warning", "caution", "loss", "volatility",
            "risco", "perda", "volatilidade"
        ],
        "liquidity": [
            "liquidity", "redemption", "withdrawal", "gating", "freeze",
            "liquidez", "resgate", "congelamento"
        ],
        "conflicts": [
            "conflict of interest", "proprietary", "self-dealing",
            "conflito de interesse"
        ],
    }

    def __init__(self, docs_dir: str = "data/raw/ubs_official"):
        self.docs_dir = Path(docs_dir)

    def process_all(self) -> List[UBSOfficialDocChunk]:
        """Processa todos os documentos oficiais"""
        all_chunks = []

        for pdf_file in self.docs_dir.glob("*.pdf"):
            try:
                chunks = self.process_document(pdf_file)
                all_chunks.extend(chunks)
                print(f"  ✓ {pdf_file.name}: {len(chunks)} chunks")
            except Exception as e:
                print(f"  ✗ {pdf_file.name}: {e}")

        return all_chunks

    def process_document(self, pdf_path: Path) -> List[UBSOfficialDocChunk]:
        """Processa um documento PDF"""
        chunks = []

        # Determinar tipo do documento pelo nome
        filename_lower = pdf_path.stem.lower()
        doc_type = self._detect_doc_type(filename_lower)

        # Extrair texto do PDF
        text_pages = self._extract_pdf_text(pdf_path)

        # Processar cada página
        for page_num, page_text in enumerate(text_pages, 1):
            if len(page_text.strip()) < 100:
                continue

            # Detectar relevância para violações
            relevant_violations = self._detect_relevant_violations(page_text)

            # Extrair quotes importantes
            important_quotes = self._extract_important_quotes(page_text)

            # Criar chunk da página
            chunk = self._create_page_chunk(
                pdf_path=pdf_path,
                doc_type=doc_type,
                page_num=page_num,
                page_text=page_text,
                relevant_violations=relevant_violations
            )

            if chunk:
                chunks.append(chunk)

            # Criar chunks adicionais para quotes importantes
            for quote in important_quotes:
                quote_chunk = self._create_quote_chunk(
                    pdf_path=pdf_path,
                    doc_type=doc_type,
                    page_num=page_num,
                    quote=quote,
                    relevant_violations=relevant_violations
                )
                if quote_chunk:
                    chunks.append(quote_chunk)

        return chunks

    def _extract_pdf_text(self, pdf_path: Path) -> List[str]:
        """Extrai texto de todas as páginas do PDF"""
        pages = []

        try:
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text = page.extract_text() or ""
                    pages.append(text)
        except Exception as e:
            print(f"Erro ao processar {pdf_path}: {e}")

        return pages

    def _detect_doc_type(self, filename: str) -> UBSOfficialChunkType:
        """Detecta tipo de documento pelo nome do arquivo"""
        filename_lower = filename.lower()
        for keyword, doc_type in self.DOC_TYPE_MAPPING.items():
            if keyword in filename_lower:
                return doc_type
        return UBSOfficialChunkType.INTERNAL_REPORT

    def _detect_relevant_violations(self, text: str) -> List[str]:
        """Detecta quais tipos de violação este texto é relevante"""
        text_lower = text.lower()
        relevant = []

        for violation_type, keywords in self.RELEVANT_SECTIONS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    relevant.append(violation_type)
                    break

        return list(set(relevant))

    def _extract_important_quotes(self, text: str, max_quotes: int = 3) -> List[str]:
        """Extrai frases importantes do texto"""
        quotes = []

        # Patterns de frases importantes
        important_patterns = [
            r"(?:must|shall|should|required to|obligated to)[^.]{20,200}\.",
            r"(?:client|investor|customer)[^.]*(?:right|entitle|protect)[^.]{10,150}\.",
            r"(?:risk|loss|volatility)[^.]*(?:may|could|might)[^.]{10,150}\.",
            r"(?:suitability|appropriate|suitable)[^.]{20,200}\.",
            r"(?:disclose|inform|communicate)[^.]*(?:must|shall|should)[^.]{10,150}\.",
        ]

        for pattern in important_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches[:max_quotes]:
                clean_match = match.strip()
                if 50 < len(clean_match) < 500:
                    quotes.append(clean_match)

        return quotes[:max_quotes]

    def _create_page_chunk(
        self,
        pdf_path: Path,
        doc_type: UBSOfficialChunkType,
        page_num: int,
        page_text: str,
        relevant_violations: List[str]
    ) -> Optional[UBSOfficialDocChunk]:
        """Cria chunk de uma página"""

        # Limitar tamanho do texto
        if len(page_text) > 2500:
            page_text = page_text[:2500] + "\n\n[...conteúdo truncado...]"

        doc_title = pdf_path.stem.replace("_", " ").replace("-", " ").title()

        content = f"""DOCUMENTO OFICIAL UBS: {doc_title}
Tipo: {doc_type.value.replace('_', ' ').title()}
Página: {page_num}

CONTEÚDO:
{page_text}

RELEVÂNCIA PARA VIOLAÇÕES: {', '.join(relevant_violations) if relevant_violations else 'Geral'}

USO NO CASO: Este documento oficial da UBS pode ser usado para demonstrar as regras e compromissos que o banco deveria seguir.
"""

        return UBSOfficialDocChunk(
            chunk_id=create_chunk_id("ubs_official", doc_type.value, f"{pdf_path.stem}_p{page_num}"),
            chunk_type=doc_type,
            content=content,
            source_document=pdf_path.name,
            source_page=page_num,
            document_title=doc_title,
            document_type="official",
            relevant_to_violations=relevant_violations,
            relevance="critical" if relevant_violations else "high"
        )

    def _create_quote_chunk(
        self,
        pdf_path: Path,
        doc_type: UBSOfficialChunkType,
        page_num: int,
        quote: str,
        relevant_violations: List[str]
    ) -> Optional[UBSOfficialDocChunk]:
        """Cria chunk para uma quote específica"""

        doc_title = pdf_path.stem.replace("_", " ").replace("-", " ").title()

        content = f"""CITAÇÃO OFICIAL UBS
Documento: {doc_title}
Página: {page_num}

CITAÇÃO EXATA:
"{quote}"

RELEVÂNCIA: Esta citação é relevante para: {', '.join(relevant_violations) if relevant_violations else 'Geral'}

USO NO CASO: Esta citação pode ser usada para demonstrar as próprias regras e compromissos da UBS, provando que o banco violou suas próprias políticas documentadas.

IMPORTÂNCIA: Documentos oficiais do próprio banco são evidências poderosas pois demonstram conhecimento prévio das obrigações.
"""

        return UBSOfficialDocChunk(
            chunk_id=create_chunk_id("ubs_official", "quote", f"{pdf_path.stem}_p{page_num}_{hash(quote) % 10000}"),
            chunk_type=doc_type,
            content=content,
            source_document=pdf_path.name,
            source_page=page_num,
            document_title=doc_title,
            document_type="official",
            exact_quote=quote,
            quote_page=page_num,
            relevant_to_violations=relevant_violations,
            relevance="critical"
        )
