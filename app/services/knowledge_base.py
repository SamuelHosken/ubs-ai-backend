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
    _base_conhecimento: Optional[Dict] = None
    _context_cache: Optional[str] = None

    @classmethod
    def load_portfolios(cls) -> None:
        """Carrega os Complete Portfolios do disco"""
        # Portfolio 01
        p01_path = cls.FORENSIC_DIR / "Complete Portfolio 01.json"
        if p01_path.exists():
            with open(p01_path, 'r', encoding='utf-8') as f:
                cls._portfolio_01 = json.load(f)
            print(f"  ✅ Carregado: Complete Portfolio 01.json")

        # Portfolio 02
        p02_path = cls.FORENSIC_DIR / "Complete Portfolio 02.json"
        if p02_path.exists():
            with open(p02_path, 'r', encoding='utf-8') as f:
                cls._portfolio_02 = json.load(f)
            print(f"  ✅ Carregado: Complete Portfolio 02.json")

        # Base de Conhecimento Adicional
        base_path = cls.FORENSIC_DIR / "base_conhecimento.json"
        if base_path.exists():
            with open(base_path, 'r', encoding='utf-8') as f:
                cls._base_conhecimento = json.load(f)
            print(f"  ✅ Carregado: base_conhecimento.json")

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

═══════════════════════════════════════════════════════════════════════════════
EVOLUÇÃO PATRIMONIAL - PORTFOLIO 01 (1998-2017)
═══════════════════════════════════════════════════════════════════════════════

┌──────┬─────────────────┬────────────────────────────────────────────────────┐
│ Ano  │ Patrimônio EUR  │ Observação                                         │
├──────┼─────────────────┼────────────────────────────────────────────────────┤
│ 1998 │ 1.310.048       │ Valor inicial (convertido de CHF)                  │
│ 1999 │ 1.174.300       │ Transição CHF → EUR                                │
│ 2000 │ 1.057.200       │ Crise dot-com                                      │
│ 2001 │ 890.900         │ Pós-crise dot-com                                  │
│ 2002 │ 780.800         │ Continuação crise                                  │
│ 2003 │ 723.500         │ Início recuperação                                 │
│ 2004 │ 674.300         │ Recuperação                                        │
│ 2005 │ 671.200         │ Estável                                            │
│ 2006 │ 637.400         │ Estável                                            │
│ 2007 │ 615.200         │ Pré-crise 2008                                     │
│ 2008 │ 477.000         │ Crise financeira global                            │
│ 2009 │ 422.900         │ Recuperação pós-crise                              │
│ 2010 │ 399.600         │ Recuperação                                        │
│ 2011 │ 370.900         │ Crise europeia                                     │
│ 2012 │ 390.200         │ Recuperação                                        │
│ 2013 │ 372.300         │ Estável                                            │
│ 2014 │ 371.900         │ Estável                                            │
│ 2015 │ 364.600         │ Estável                                            │
│ 2016 │ 229.400         │ Grande saque de EUR 140.700                        │
│ 2017 │ 229.700         │ Valor final                                        │
└──────┴─────────────────┴────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
RETORNOS ANUAIS (TWR%) - PORTFOLIO 01
═══════════════════════════════════════════════════════════════════════════════

┌──────┬────────────┬────────────────┬───────────────────────────────────────┐
│ Ano  │ TWR %      │ Acumulado %    │ Contexto                              │
├──────┼────────────┼────────────────┼───────────────────────────────────────┤
│ 2000 │ -2,00%     │ -2,00%         │ Crise dot-com                         │
│ 2001 │ -8,85%     │ -10,67%        │ Pós-11 de setembro                    │
│ 2002 │ -10,35%    │ -19,91%        │ Enron/WorldCom                        │
│ 2003 │ +4,25%     │ -16,49%        │ Início recuperação                    │
│ 2004 │ +2,62%     │ -14,28%        │ Recuperação                           │
│ 2005 │ +8,74%     │ -6,79%         │ Bom ano                               │
│ 2006 │ +2,57%     │ -4,39%         │ Estável                               │
│ 2007 │ +0,32%     │ -4,09%         │ Pré-crise                             │
│ 2008 │ -17,73%    │ -21,28%        │ CRISE FINANCEIRA GLOBAL               │
│ 2009 │ +11,26%    │ -8,17%         │ Recuperação forte                     │
│ 2010 │ +5,19%     │ -3,41%         │ Recuperação                           │
│ 2011 │ -2,46%     │ -5,79%         │ Crise europeia                        │
│ 2012 │ +8,34%     │ +2,07%         │ Recuperação - volta ao positivo       │
│ 2013 │ +5,14%     │ +7,32%         │ Bom ano                               │
│ 2014 │ +6,54%     │ +14,35%        │ Bom ano                               │
│ 2015 │ +1,41%     │ +15,96%        │ Estável                               │
│ 2016 │ +1,32%     │ +17,49%        │ Estável                               │
│ 2017 │ +0,15%     │ +17,66%        │ Período parcial (Jan)                 │
└──────┴────────────┴────────────────┴───────────────────────────────────────┘

RESUMO RETORNOS P01:
- Performance Cumulativa Final (2006-2017): +17,65%
- Média Anual: +1,63%
- Melhor Ano: 2009 (+11,26%)
- Pior Ano: 2008 (-17,73%)
- Anos Positivos: 12 de 17
- Win Rate: 70,6%
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

═══════════════════════════════════════════════════════════════════════════════
EVOLUÇÃO PATRIMONIAL - PORTFOLIO 02 (2009-2017)
═══════════════════════════════════════════════════════════════════════════════

┌──────┬─────────────────┬────────────────────────────────────────────────────┐
│ Ano  │ Patrimônio EUR  │ Observação                                         │
├──────┼─────────────────┼────────────────────────────────────────────────────┤
│ 2009 │ 28.600          │ Valor inicial (Fev/2009) - FUNDO JÁ TRAVADO        │
│ 2009 │ 20.800          │ Fim do ano - Perda de -27,44%                      │
│ 2010 │ 17.300          │ Perda adicional de -16,62%                         │
│ 2011 │ 15.400          │ Primeiro ano com resgates possíveis                │
│ 2012 │ 12.500          │ Patrimônio em queda                                │
│ 2013 │ 8.300           │ PIOR MOMENTO: -47,40% acumulado                    │
│ 2014 │ 6.500           │ Início recuperação                                 │
│ 2015 │ 3.600           │ Após resgates                                      │
│ 2016 │ 2.700           │ Próximo ao fim                                     │
│ 2017 │ 2.700           │ Valor final                                        │
└──────┴─────────────────┴────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
RESGATES POR ANO - PORTFOLIO 02
═══════════════════════════════════════════════════════════════════════════════

┌──────┬─────────────┬────────────────────────────────────────────────────────┐
│ Ano  │ Resgate EUR │ Observação                                             │
├──────┼─────────────┼────────────────────────────────────────────────────────┤
│ 2009 │ 0           │ FUNDO TRAVADO (gating) - cliente não podia sacar       │
│ 2010 │ 0           │ FUNDO TRAVADO (gating) - cliente não podia sacar       │
│ 2011 │ 2.700       │ Primeiras retiradas possíveis após desbloqueio parcial │
│ 2012 │ 3.000       │ Resgates limitados                                     │
│ 2013 │ 2.100       │ Resgates limitados                                     │
│ 2014 │ 2.600       │ Resgates limitados                                     │
│ 2015 │ 3.900       │ Maior resgate do período                               │
│ 2016 │ 1.000       │ Resgate final                                          │
│ 2017 │ 0           │ Sem resgates (período parcial)                         │
├──────┼─────────────┼────────────────────────────────────────────────────────┤
│TOTAL │ 15.300      │ Total de resgates realizados                           │
└──────┴─────────────┴────────────────────────────────────────────────────────┘

IMPORTANTE: Os resgates NÃO explicam a perda. Quando começaram (2011),
o patrimônio já havia caído de EUR 28.600 para EUR 15.400 (-46%).

═══════════════════════════════════════════════════════════════════════════════
PERFORMANCE CUMULATIVA - PORTFOLIO 02
═══════════════════════════════════════════════════════════════════════════════

┌──────┬────────────┬────────────────┬───────────────────────────────────────┐
│ Ano  │ TWR %      │ Acumulado %    │ Observação                            │
├──────┼────────────┼────────────────┼───────────────────────────────────────┤
│ 2009 │ -27,44%    │ -27,44%        │ FUNDO TRAVADO - Cliente preso         │
│ 2010 │ -16,62%    │ -39,50%        │ FUNDO TRAVADO - Cliente preso         │
│ 2011 │ +4,30%     │ -36,90%        │ Primeira recuperação                  │
│ 2012 │ -0,25%     │ -37,05%        │ Estagnação                            │
│ 2013 │ -16,44%    │ -47,40%        │ PIOR MOMENTO - Violação de tolerância │
│ 2014 │ +11,02%    │ -41,60%        │ Recuperação                           │
│ 2015 │ +16,45%    │ -32,00%        │ Melhor ano                            │
│ 2016 │ +0,18%     │ -31,88%        │ Estável                               │
│ 2017 │ +1,09%     │ -31,13%        │ Performance final                     │
└──────┴────────────┴────────────────┴───────────────────────────────────────┘

RESUMO PERFORMANCE P02:
- Performance Cumulativa Final: -31,13%
- Média Anual: -4,58%
- Melhor Ano: 2015 (+16,45%)
- Pior Ano: 2009 (-27,44%)
- Pior Momento: 2013 (-47,40% acumulado)
- Tolerância do Perfil: -20%
- Violação da Tolerância: 27,40 pontos percentuais além do limite

ANÁLISE DE VIOLAÇÃO:
┌─────────────────────────┬──────────────┬──────────────────────────────────┐
│ Métrica                 │ Valor        │ Análise                          │
├─────────────────────────┼──────────────┼──────────────────────────────────┤
│ Tolerância Máxima       │ -20%         │ Perfil Classe C (Yield)          │
│ Perda Final             │ -31,13%      │ 11,13pp acima do limite          │
│ Pior Momento            │ -47,40%      │ 27,40pp acima do limite          │
│ Anos em Violação        │ 6 de 9       │ 2010, 2011, 2012, 2013, 2014, 15 │
│ Excesso Máximo          │ 137%         │ Perda 2,37x o limite tolerado    │
└─────────────────────────┴──────────────┴──────────────────────────────────┘
""")

        # =========================================================
        # CONHECIMENTO ADICIONAL
        # =========================================================
        if cls._base_conhecimento:
            bc = cls._base_conhecimento

            # Evolução Patrimonial Completa
            context_parts.append("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    CONHECIMENTO ADICIONAL                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

═══════════════════════════════════════════════════════════════════════════════
DADOS DO CLIENTE
═══════════════════════════════════════════════════════════════════════════════
- Cliente: CQUE 913017
- Banco: UBS Switzerland AG
- Assessor: Philippe Poisson (Crans-Montana)
- Telefone: +41 27 486 91 22
- Email: philippe.poisson@ubs.com
- Perfil: C - Yield (conservador, tolerância -20%)
- Período de análise: 1998-2017 (19 anos)
- Moeda base: EUR (desde 1999, antes CHF)

═══════════════════════════════════════════════════════════════════════════════
EVOLUÇÃO PATRIMONIAL COMPLETA (1998-2017)
═══════════════════════════════════════════════════════════════════════════════

MARCOS IMPORTANTES:
- Nov/1998: CHF 2.034.713 → PICO ABSOLUTO (equivalente ~EUR 1.270.000)
- Dez/1999: EUR 1.174.300 → Conversão para Euro
- Ago/2000: EUR 1.251.769 → PICO EM EUROS (antes crash dot-com)
- Dez/2002: EUR 780.800 → Fundo do crash dot-com
- Dez/2005: EUR 673.794 → Entrada no Property Fund
- Dez/2008: EUR 477.029 → CRISE FINANCEIRA GLOBAL
- Dez/2017: EUR 3.312 → LIQUIDAÇÃO QUASE TOTAL

CAUSAS DA QUEDA DE -99,74%:
- Saques do cliente: EUR 1.148.900 (95% da causa)
- Perdas de mercado P01: EUR 47.000 (4%)
- Perdas P02: EUR 26.000 (1%)

═══════════════════════════════════════════════════════════════════════════════
CRISE 2008 - DETALHES
═══════════════════════════════════════════════════════════════════════════════

Performance anual: -17,73%
Valor inicial: EUR 615.200
Valor final: EUR 477.029
Perda absoluta: EUR 138.171

TRIMESTRAL:
- Q1 2008: -4,66%
- Q2 2008: -1,97%
- Q3 2008: -3,50%
- Q4 2008: -8,78% (Colapso Lehman Brothers)

MENSAL:
- Setembro: -5,00% (Lehman faliu 15/09)
- Outubro: -5,00% (Pânico global)

═══════════════════════════════════════════════════════════════════════════════
PROPERTY FUND - UBS GLOBAL PROPERTY FUND LTD
═══════════════════════════════════════════════════════════════════════════════

ISIN: GB00B0386M46
Classe: C-EUR-acc

HISTÓRICO DE COTAS:
- Dez/2005: 1.375 cotas | Preço: EUR 10,74 | Valor: EUR 14.768
- Dez/2008: 2.815 cotas | Preço: EUR 11,02 | Valor: EUR 31.009 | GATING!
- Jan/2017: 157 cotas | Preço: EUR 6,92 | Valor: EUR 2.692
- Dez/2017: 157 cotas | Preço: EUR 6,92 | Valor: EUR 1.088

PROBLEMA: Cotas reduzidas de 2.815 para 157 através de resgates parciais
quando liquidez foi liberada (após anos de espera).

═══════════════════════════════════════════════════════════════════════════════
MOEDAS - ANTES E DEPOIS DO EURO
═══════════════════════════════════════════════════════════════════════════════

EM 1998 (PRÉ-EURO):
- CHF (Franco Suíço): 61%
- DEM (Marco Alemão): 13% → EXTINTA em 2002 (1 EUR = 1,95583 DEM)
- USD (Dólar): 10%
- XEU (ECU): 9% → VIROU EURO em 1999 (1 EUR = 1 XEU)
- GBP (Libra): 2%
- FRF (Franco Francês): 1% → EXTINTA em 2002 (1 EUR = 6,55957 FRF)

EM 2017:
- EUR: 84%
- USD: 10%
- Outras: 6%

═══════════════════════════════════════════════════════════════════════════════
AÇÕES INDIVIDUAIS (1998)
═══════════════════════════════════════════════════════════════════════════════

Em 1998 o portfolio tinha ações suíças individuais:
- Roche Holding: +571,51% ✅ (MELHOR AÇÃO)
- UBS: +97,67% (quase dobrou)
- Zurich Insurance: +16,45%
- Novartis: +13,49%
- Credit Suisse: -36,81% ❌ (PIOR AÇÃO)

Depois foram substituídas por fundos de investimento.

═══════════════════════════════════════════════════════════════════════════════
PERFIS DE INVESTIMENTO UBS
═══════════════════════════════════════════════════════════════════════════════

O cliente tinha perfil C - YIELD (conservador):

┌────────┬────────────────┬─────────┬─────────────┬───────────┬───────────┐
│ Código │ Nome           │ Retorno │ Volatilidade│ Perda Max │ Horizonte │
├────────┼────────────────┼─────────┼─────────────┼───────────┼───────────┤
│ A      │ Fixed Income   │ ~1%     │ ~4%         │ -15%      │ 2 anos    │
│ B      │ Income         │ ~2%     │ ~5%         │ -17%      │ 3 anos    │
│ C      │ Yield          │ ~3%     │ ~6%         │ -20%      │ 4 anos    │ ← CLIENTE
│ D      │ Balanced       │ ~4%     │ ~8%         │ -30%      │ 5 anos    │
│ E      │ Growth         │ ~5%     │ ~10%        │ -40%      │ 7 anos    │
│ F      │ Equities       │ ~6%     │ ~13%        │ -45%      │ 8 anos    │
└────────┴────────────────┴─────────┴─────────────┴───────────┴───────────┘

═══════════════════════════════════════════════════════════════════════════════
TAXAS UBS
═══════════════════════════════════════════════════════════════════════════════

- Money Market Funds: até 1,00%/ano
- Bond Funds: 0,25% - 2,05%/ano
- Equity Funds: até 2,30%/ano
- Asset Allocation Funds: 0,50% - 0,80%/ano
- Hedge Funds: 0,65% - 2,30%/ano
- Real Estate Funds: 0,60% - 1,50%/ano
- Structured Products: até 3,00% (upfront)

═══════════════════════════════════════════════════════════════════════════════
GLOSSÁRIO
═══════════════════════════════════════════════════════════════════════════════

- TWR: Time-Weighted Return - Retorno ponderado pelo tempo, neutraliza saques
- Gating: Suspensão temporária de resgates, geralmente por falta de liquidez
- Suitability: Adequação - verificar se produto é apropriado para o perfil
- NAV: Net Asset Value - Valor líquido dos ativos
- Hedge Fund: Fundo alternativo com estratégias sofisticadas
- Alternative Investments: Hedge funds, private equity, commodities

═══════════════════════════════════════════════════════════════════════════════
ALOCAÇÃO DE ATIVOS POR ANO (ASSET ALLOCATION)
═══════════════════════════════════════════════════════════════════════════════

TABELA COMPLETA DE ALOCAÇÃO (%):
┌──────────┬───────┬──────────┬─────────┬───────────┬───────┬─────────────┐
│ Data     │ Bonds │ Equities │ Alt.Inv │ RealEstate│ Cash  │ Total EUR   │
├──────────┼───────┼──────────┼─────────┼───────────┼───────┼─────────────┤
│ Nov/1998 │ 51%   │ 24%      │ 0%      │ 0%        │ 25%   │ CHF 2.034M  │
│ Ago/2000 │ 49%   │ 47%      │ 0%      │ 0%        │ 4%    │ EUR 1.251M  │
│ Dez/2005 │ 48%   │ 26%      │ 15%     │ 2%        │ 5%    │ EUR 673K    │
│ Dez/2008 │ 45%   │ 22%      │ 19%     │ 7%        │ 3%    │ EUR 477K    │
│ Mar/2013 │ 56%   │ 28%      │ 15%     │ 0%*       │ 2%    │ EUR 380K    │
│ Jun/2014 │ 56%   │ 27%      │ 16%     │ 0%*       │ 1%    │ EUR 371K    │
│ Jun/2016 │ 51%   │ 25%      │ 20%     │ 0%*       │ 3%    │ EUR 356K    │
│ Jan/2017 │ 51%   │ 24%      │ 20%     │ 1%*       │ 5%    │ EUR 229K    │
└──────────┴───────┴──────────┴─────────┴───────────┴───────┴─────────────┘
*Real Estate ficou separado no Portfolio 02 após gating

DETALHES AGOSTO 2000 (PICO - Bolha Dot-com):
- Bonds: EUR 610.988 (49%)
- Equities: EUR 588.107 (47%) ← MUITO ALTO para perfil conservador!
- Money Market: EUR 52.674 (4%)
- Total: EUR 1.251.769

DETALHES DEZEMBRO 2008 (Crise Financeira):
- Bonds: EUR 213.455 (45%)
- Equities: EUR 103.217 (22%)
- Alternative Investments: EUR 91.842 (19%)
  - UBS Multi-Strategy Alternative Fund: EUR 54.139 (11,35%) | +0,26%
  - UBS Multi-Manager Alternative Fund II: EUR 30.572 (6,41%) | -11,74%
  - UBS Multi-Manager Alternative Fund SPC: EUR 7.131 (1,49%) | -20,11%
- Real Estate: EUR 31.009 (7%) - 2.815 cotas | GATING!
- Asset Allocation Funds: EUR 15.219 (3%)
- Money Market: EUR 15.450 (3%)
- Precious Metals: EUR 7.835 (2%) | -18,90%
- Total: EUR 477.029

DETALHES JANEIRO 2017 (Pré-liquidação):
- Bonds: EUR 116.920 (51%)
- Equities: EUR 55.421 (24%)
- Hedge Funds: EUR 45.994 (20%)
  - Key Multi-Manager Hedge Fund - Diversified: EUR 34.531 (15%) | +22,72%
  - DCI Diversified Credit Investment: EUR 11.463 (5%) | +39,18%
- Liquidity: EUR 11.376 (5%)
- Total P01: EUR 229.711
- P02 (separado): EUR 2.692 (Property Fund - 157 cotas)

EVOLUÇÃO DOS ALTERNATIVE INVESTMENTS (Hedge Funds):
- 1998: 0% (não existiam)
- 2000: 0%
- 2003: Início dos hedge funds
- 2005: 15% (Quellos + UBS Multi-Strategy)
- 2008: 19% (UBS Multi-Strategy 11% + Multi-Manager II 6%)
- 2016: 20%
- 2017: 20% (Key Multi-Manager 15% + DCI Credit 5%)

EVOLUÇÃO DO REAL ESTATE:
- 1998-2004: 0%
- Dez/2005: 2% (entrada - 1.375 cotas, EUR 14.768)
- Dez/2008: 7% (pico - 2.815 cotas, EUR 31.009) → GATING
- 2009-2016: Separado no P02 (travado)
- Jan/2017: 1% (157 cotas, EUR 2.692)

TENDÊNCIAS OBSERVADAS:
1. Bonds sempre dominantes (45-56%) - consistente com perfil Yield
2. Equities variaram muito (22-47%) - pico perigoso em 2000
3. Alternative Investments cresceram (0% → 20%)
4. Real Estate problemático - entrou em 2005, congelou em 2008
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
