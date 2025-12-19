"""
Knowledge Base - Carrega os Complete Portfolios como contexto fixo.
Esses dados SEMPRE serão incluídos nas respostas da IA.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional


class KnowledgeBase:
    """Base de conhecimento com dados fixos dos portfolios"""

    # Caminho dos arquivos de conhecimento
    FORENSIC_DIR = Path(__file__).parent.parent.parent / "data" / "raw" / "forensic"

    # Cache dos dados
    _portfolio_01: Optional[Dict] = None
    _portfolio_02: Optional[Dict] = None
    _context_cache: Optional[str] = None

    @classmethod
    def load_portfolios(cls) -> None:
        """Carrega os Complete Portfolios do disco"""
        # Portfolio 01
        p01_path = cls.FORENSIC_DIR / "Complete Portfolio 01.json"
        if p01_path.exists():
            with open(p01_path, 'r', encoding='utf-8') as f:
                cls._portfolio_01 = json.load(f)
            print(f"  Carregado: Complete Portfolio 01.json")

        # Portfolio 02
        p02_path = cls.FORENSIC_DIR / "Complete Portfolio 02.json"
        if p02_path.exists():
            with open(p02_path, 'r', encoding='utf-8') as f:
                cls._portfolio_02 = json.load(f)
            print(f"  Carregado: Complete Portfolio 02.json")

    @classmethod
    def get_fixed_context(cls) -> str:
        """
        Retorna o contexto fixo que SEMPRE deve ser incluído nas respostas.
        Contém os dados principais dos dois portfolios.
        """
        if cls._context_cache:
            return cls._context_cache

        # Carregar se ainda não carregou
        if cls._portfolio_01 is None:
            cls.load_portfolios()

        context_parts = []

        # =========================================================
        # PORTFOLIO 01 - DADOS COMPLETOS
        # =========================================================
        if cls._portfolio_01:
            p01 = cls._portfolio_01
            resumo = p01.get("resumo_executivo", {})

            context_parts.append("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PORTFOLIO 01 - DADOS COMPLETOS                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

RESUMO:
- Conta: UBS Switzerland AG | 268-913017-01
- Período: 1999 a 2017
- Valor Inicial (Dez/1999): EUR 1.174.300
- Valor Final (Jan/2017): EUR 229.700
- Total de Aportes: EUR 236.000
- Total de Saques: EUR 1.133.600
- Saques Líquidos: EUR 897.600
- Perda de Performance: EUR 47.000 (apenas 5%)
- Percentual Recuperado: 96,7%

CONCLUSÃO: 95% da redução patrimonial foi causada por SAQUES do próprio cliente.
Apenas 5% foram perdas de investimento.

═══════════════════════════════════════════════════════════════════════════════
TABELA DE RETIRADAS (SAQUES) - PORTFOLIO 01 - ANO A ANO
═══════════════════════════════════════════════════════════════════════════════

PERÍODO 1999-2008 (Fonte: Statement 31.12.2008):
┌──────┬────────────┬───────────┬───────────┬──────────┬──────────┐
│ Ano  │ Início EUR │ Entrada   │ Saída     │ Final    │ Perf EUR │
├──────┼────────────┼───────────┼───────────┼──────────┼──────────┤
│ 2000 │ 1.174.300  │ +163.600  │ -256.400  │ 1.057.200│ -23.800  │
│ 2001 │ 1.057.200  │ 0         │ -73.800   │ 890.900  │ -92.500  │
│ 2002 │ 890.900    │ +57.100   │ -77.900   │ 780.800  │ -89.300  │
│ 2003 │ 780.800    │ 0         │ -88.600   │ 723.500  │ +31.400  │
│ 2004 │ 723.500    │ 0         │ -67.500   │ 674.300  │ +18.200  │
│ 2005 │ 674.300    │ 0         │ -59.400   │ 671.200  │ +56.300  │
│ 2006 │ 671.200    │ 0         │ -50.200   │ 637.400  │ +16.400  │
│ 2007 │ 637.400    │ 0         │ -24.400   │ 615.200  │ +2.200   │
│ 2008 │ 615.200    │ 0         │ -32.300   │ 477.000  │ -105.900 │
└──────┴────────────┴───────────┴───────────┴──────────┴──────────┘

PERÍODO 2006-2017 (Fonte: Statement 20.01.2017):
┌─────────┬────────────┬───────────┬───────────┬──────────┬──────────┐
│ Período │ Início EUR │ Entrada   │ Saída     │ Final    │ Perf EUR │
├─────────┼────────────┼───────────┼───────────┼──────────┼──────────┤
│ 2006-07 │ 637.400    │ 0         │ -24.400   │ 615.200  │ +2.200   │
│ 2007-08 │ 615.200    │ 0         │ -32.300   │ 477.000  │ -105.900 │
│ 2008-09 │ 477.000    │ 0         │ -99.700   │ 422.900  │ +45.600  │
│ 2009-10 │ 422.900    │ 0         │ -44.200   │ 399.600  │ +20.900  │
│ 2010-11 │ 399.600    │ +2.700    │ -22.000   │ 370.900  │ -9.300   │
│ 2011-12 │ 370.900    │ +3.000    │ -14.200   │ 390.200  │ +30.500  │
│ 2012-13 │ 390.200    │ +2.100    │ -39.000   │ 372.300  │ +19.000  │
│ 2013-14 │ 372.300    │ +2.600    │ -26.700   │ 371.900  │ +23.700  │
│ 2014-15 │ 371.900    │ +3.900    │ -16.600   │ 364.600  │ +5.500   │
│ 2015-16 │ 364.600    │ +1.000    │ -140.700  │ 229.400  │ +4.500   │
│ 2016-17 │ 229.400    │ 0         │ 0         │ 229.700  │ +300     │
└─────────┴────────────┴───────────┴───────────┴──────────┴──────────┘

LISTA DE SAQUES (RETIRADAS) POR ANO - PORTFOLIO 01:
- 2000: EUR 256.400 (saque)
- 2001: EUR 73.800 (saque)
- 2002: EUR 77.900 (saque)
- 2003: EUR 88.600 (saque)
- 2004: EUR 67.500 (saque)
- 2005: EUR 59.400 (saque)
- 2006: EUR 50.200 (saque)
- 2007: EUR 24.400 (saque)
- 2008: EUR 32.300 (saque)
- 2009: EUR 99.700 (saque)
- 2010: EUR 44.200 (saque)
- 2011: EUR 22.000 (saque)
- 2012: EUR 14.200 (saque)
- 2013: EUR 39.000 (saque)
- 2014: EUR 26.700 (saque)
- 2015: EUR 16.600 (saque)
- 2016: EUR 140.700 (saque - maior saque da série)
- 2017: EUR 0 (sem saque)

TOTAL DE SAQUES 1999-2008: EUR 730.500
TOTAL DE SAQUES 2006-2017: EUR 459.800
TOTAL GERAL DE SAQUES: EUR 1.133.600
""")

        # =========================================================
        # PORTFOLIO 02 - DADOS COMPLETOS
        # =========================================================
        if cls._portfolio_02:
            context_parts.append("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PORTFOLIO 02 - DADOS COMPLETOS                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

RESUMO:
- Conta: UBS Switzerland AG | 268-913017-02
- Produto: UBS Global Property Fund Ltd (ISIN: GB00B0386M46)
- Período: Fevereiro 2009 a Dezembro 2017
- Valor Inicial (Fev/2009): EUR 29.408
- Valor Final (2017): EUR ~2.700
- Total de Saques: EUR 15.300
- Perda de Performance: EUR ~11.400 (38,8%)
- Perda Total: -93,2%
- Perfil do Cliente: "Yield" (C) - CONSERVADOR (tolerância 20%)

PROBLEMA CRÍTICO: O cliente foi alocado 3 MESES APÓS o fundo ser CONGELADO (gating).
O fundo foi congelado em DEZ/2008. Cliente entrou em FEV/2009.

═══════════════════════════════════════════════════════════════════════════════
TABELA DE OUTFLOWS (SAQUES) - PORTFOLIO 02 - ANO A ANO
═══════════════════════════════════════════════════════════════════════════════

┌──────┬─────────────┬───────────────┬─────────────────────────────────────────┐
│ Ano  │ Outflow EUR │ Performance % │ Observação                              │
├──────┼─────────────┼───────────────┼─────────────────────────────────────────┤
│ 2009 │ 0           │ -27,44%       │ FUNDO TRAVADO - Cliente NÃO podia sacar │
│ 2010 │ 0           │ -16,62%       │ FUNDO TRAVADO - Cliente NÃO podia sacar │
│ 2011 │ 2.700       │ +4,30%        │ Primeiras retiradas possíveis           │
│ 2012 │ 3.000       │ -0,25%        │                                         │
│ 2013 │ 2.100       │ -16,44%       │                                         │
│ 2014 │ 2.600       │ +11,02%       │                                         │
│ 2015 │ 3.900       │ +16,45%       │                                         │
│ 2016 │ 1.000       │ -1,55%        │                                         │
└──────┴─────────────┴───────────────┴─────────────────────────────────────────┘

TOTAL DE SAQUES P02: EUR 15.300

LISTA DE SAQUES POR ANO - PORTFOLIO 02:
- 2009: EUR 0 (fundo travado)
- 2010: EUR 0 (fundo travado)
- 2011: EUR 2.700
- 2012: EUR 3.000
- 2013: EUR 2.100
- 2014: EUR 2.600
- 2015: EUR 3.900
- 2016: EUR 1.000

VIOLAÇÕES IDENTIFICADAS:
1. Conflito de interesses - Produto próprio UBS
2. Negligência grosseira - Alocação 3 meses após gating
3. Violação de suitability - Perda 47% vs tolerância 20%
4. Concentração inadequada - 100% em produto ilíquido
5. Falha no dever de cuidado - 5 anos sem intervenção

RESPONSABILIDADE:
- UBS: 90% de culpa
- Mercado: 10%
- Cliente: 0% (estava preso, não teve escolha)
""")

        cls._context_cache = "\n".join(context_parts)
        return cls._context_cache

    @classmethod
    def get_portfolio_01_withdrawals(cls) -> Dict[str, float]:
        """Retorna os saques do Portfolio 01 por ano"""
        return {
            "2000": 256.4,
            "2001": 73.8,
            "2002": 77.9,
            "2003": 88.6,
            "2004": 67.5,
            "2005": 59.4,
            "2006": 50.2,
            "2007": 24.4,
            "2008": 32.3,
            "2009": 99.7,
            "2010": 44.2,
            "2011": 22.0,
            "2012": 14.2,
            "2013": 39.0,
            "2014": 26.7,
            "2015": 16.6,
            "2016": 140.7,
        }

    @classmethod
    def get_portfolio_02_withdrawals(cls) -> Dict[str, float]:
        """Retorna os saques do Portfolio 02 por ano"""
        return {
            "2009": 0,
            "2010": 0,
            "2011": 2.7,
            "2012": 3.0,
            "2013": 2.1,
            "2014": 2.6,
            "2015": 3.9,
            "2016": 1.0,
        }


# Carregar na inicialização
print("Carregando Knowledge Base...")
KnowledgeBase.load_portfolios()
