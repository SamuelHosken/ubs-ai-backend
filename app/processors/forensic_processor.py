"""
Processador de Relatórios Forenses.
Processa arquivos Markdown de análise forense e gera chunks para o RAG.
"""
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.models.chunks import (
    ForensicChunk,
    ViolationChunk,
    ForensicChunkType,
    create_chunk_id
)


class ForensicProcessor:
    """Processa relatórios forenses em Markdown"""

    def __init__(self, forensic_dir: str = "data/raw/forensic"):
        self.forensic_dir = Path(forensic_dir)

    def process_all(self) -> List[ForensicChunk]:
        """Processa todos os relatórios forenses"""
        all_chunks = []

        for md_file in self.forensic_dir.glob("*.md"):
            try:
                chunks = self.process_forensic_file(md_file)
                all_chunks.extend(chunks)
                print(f"  ✓ {md_file.name}: {len(chunks)} chunks")
            except Exception as e:
                print(f"  ✗ {md_file.name}: {e}")

        return all_chunks

    def process_forensic_file(self, md_path: Path) -> List[ForensicChunk]:
        """Processa um arquivo Markdown de análise forense"""
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()

        chunks = []
        source_doc = md_path.stem

        # Dividir por seções (headers ##)
        sections = self._split_by_sections(content)

        for section_title, section_content in sections:
            # Determinar tipo de chunk pela seção
            chunk_type = self._detect_chunk_type(section_title, section_content)

            # Criar chunk apropriado
            if chunk_type == ForensicChunkType.VIOLATION:
                chunk = self._create_violation_chunk(section_title, section_content, source_doc)
            else:
                chunk = self._create_forensic_chunk(section_title, section_content, source_doc, chunk_type)

            if chunk:
                chunks.append(chunk)

        return chunks

    def _split_by_sections(self, content: str) -> List[tuple]:
        """Divide o conteúdo em seções pelo header ##"""
        sections = []

        # Pattern para headers de nível 1 e 2
        pattern = r'^(#{1,2})\s+(.+?)$'
        lines = content.split('\n')

        current_title = "Introdução"
        current_content = []

        for line in lines:
            match = re.match(pattern, line)
            if match:
                # Salvar seção anterior
                if current_content:
                    sections.append((current_title, '\n'.join(current_content)))

                current_title = match.group(2).strip()
                current_content = []
            else:
                current_content.append(line)

        # Última seção
        if current_content:
            sections.append((current_title, '\n'.join(current_content)))

        return sections

    def _detect_chunk_type(self, title: str, content: str) -> ForensicChunkType:
        """Detecta o tipo de chunk baseado no título e conteúdo"""
        title_lower = title.lower()
        content_lower = content.lower()

        # Violações
        if any(word in title_lower for word in ['violação', 'violation', 'suitability', 'disclosure']):
            return ForensicChunkType.VIOLATION

        # Evidências
        if any(word in title_lower for word in ['evidência', 'evidence', 'prova', 'fonte']):
            return ForensicChunkType.EVIDENCE

        # Conclusões
        if any(word in title_lower for word in ['conclusão', 'conclusion', 'resultado']):
            return ForensicChunkType.CONCLUSION

        # Recomendações
        if any(word in title_lower for word in ['recomendação', 'recommendation', 'próximos']):
            return ForensicChunkType.RECOMMENDATION

        # Default: análise
        return ForensicChunkType.ANALYSIS

    def _create_forensic_chunk(
        self, title: str, content: str, source_doc: str, chunk_type: ForensicChunkType
    ) -> Optional[ForensicChunk]:
        """Cria um chunk forense genérico"""
        if len(content.strip()) < 50:
            return None

        # Limitar tamanho
        if len(content) > 3000:
            content = content[:3000] + "\n\n[...conteúdo truncado...]"

        # Detectar severidade
        severity = self._detect_severity(content)

        # Detectar portfolio afetado
        portfolio_affected = None
        if "portfolio 02" in content.lower() or "mandate re" in content.lower():
            portfolio_affected = "02"
        elif "portfolio 01" in content.lower():
            portfolio_affected = "01"
        elif "ambos" in content.lower() or "both" in content.lower():
            portfolio_affected = "both"

        # Extrair referências de evidência
        evidence_refs = self._extract_evidence_refs(content)

        return ForensicChunk(
            chunk_id=create_chunk_id("forensic", chunk_type.value, f"{source_doc}_{title[:30]}"),
            chunk_type=chunk_type,
            content=f"# {title}\n\n{content}",
            source_document=source_doc,
            portfolio_affected=portfolio_affected,
            severity=severity,
            evidence_refs=evidence_refs,
            relevance="critical" if severity in ["critical", "grave"] else "high"
        )

    def _create_violation_chunk(
        self, title: str, content: str, source_doc: str
    ) -> Optional[ViolationChunk]:
        """Cria um chunk específico de violação"""
        if len(content.strip()) < 50:
            return None

        # Limitar tamanho
        if len(content) > 3000:
            content = content[:3000] + "\n\n[...conteúdo truncado...]"

        # Detectar tipo de violação
        violation_category = self._detect_violation_category(title, content)

        # Detectar severidade
        severity = self._detect_severity(content)

        # Detectar impacto financeiro
        financial_impact = self._extract_financial_impact(content)

        # Detectar portfolio afetado
        portfolio_affected = None
        if "portfolio 02" in content.lower() or "mandate re" in content.lower():
            portfolio_affected = "02"
        elif "portfolio 01" in content.lower():
            portfolio_affected = "01"

        return ViolationChunk(
            chunk_id=create_chunk_id("forensic", "violation", f"{source_doc}_{title[:30]}"),
            chunk_type=ForensicChunkType.VIOLATION,
            content=f"# {title}\n\n{content}",
            source_document=source_doc,
            portfolio_affected=portfolio_affected,
            violation_type=violation_category,
            violation_category=violation_category,
            severity=severity,
            evidence_refs=self._extract_evidence_refs(content),
            financial_impact_eur=financial_impact,
            relevance="critical"
        )

    def _detect_severity(self, content: str) -> str:
        """Detecta severidade baseada no conteúdo"""
        content_lower = content.lower()

        if any(word in content_lower for word in ['crítico', 'critical', 'grave', 'severe', '-93%', '-90%']):
            return "critical"
        elif any(word in content_lower for word in ['sério', 'serious', 'significant', 'major']):
            return "grave"
        elif any(word in content_lower for word in ['moderado', 'moderate', 'médio']):
            return "moderate"
        else:
            return "moderate"

    def _detect_violation_category(self, title: str, content: str) -> str:
        """Detecta categoria da violação"""
        combined = (title + " " + content).lower()

        if "suitability" in combined or "perfil" in combined or "adequação" in combined:
            return "suitability"
        elif "disclosure" in combined or "divulgação" in combined or "informação" in combined:
            return "disclosure"
        elif "fiduciary" in combined or "fiduciário" in combined or "dever" in combined:
            return "fiduciary"
        elif "conflict" in combined or "conflito" in combined:
            return "conflicts"
        elif "timing" in combined or "momento" in combined or "congelado" in combined:
            return "timing"
        else:
            return "general"

    def _extract_evidence_refs(self, content: str) -> List[Dict[str, Any]]:
        """Extrai referências de evidência do conteúdo"""
        refs = []

        # Pattern para [PDF: xxx] ou [Fonte: xxx]
        pdf_pattern = r'\[PDF:\s*([^\]]+)\]'
        fonte_pattern = r'\[Fonte:\s*([^\]]+)\]'

        for match in re.findall(pdf_pattern, content):
            refs.append({"type": "document", "source": match.strip()})

        for match in re.findall(fonte_pattern, content):
            refs.append({"type": "source", "source": match.strip()})

        return refs

    def _extract_financial_impact(self, content: str) -> Optional[float]:
        """Extrai impacto financeiro do conteúdo"""
        # Procurar por valores em EUR
        pattern = r'EUR\s*([\d.,]+)'
        matches = re.findall(pattern, content)

        if matches:
            try:
                # Pegar o maior valor encontrado
                values = []
                for m in matches:
                    clean = m.replace('.', '').replace(',', '.')
                    values.append(float(clean))
                return max(values) if values else None
            except:
                pass

        return None
