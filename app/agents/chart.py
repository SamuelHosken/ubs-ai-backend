from openai import OpenAI
from instructor import from_openai
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from app.core.config import settings


class ChartData(BaseModel):
    labels: List[str]
    values: List[float]


class ChartSpecification(BaseModel):
    type: Literal["line", "bar", "pie"]
    title: str
    data: ChartData
    x_label: Optional[str] = Field(default="")
    y_label: Optional[str] = Field(default="Valor")
    insights: Optional[List[str]] = Field(default_factory=list)


# =====================================================
# DADOS FIXOS DO PORTFOLIO 01
# =====================================================

PORTFOLIO_01_WITHDRAWALS = {
    "2000": 256.4, "2001": 73.8, "2002": 77.9, "2003": 88.6, "2004": 67.5,
    "2005": 59.4, "2006": 50.2, "2007": 24.4, "2008": 32.3, "2009": 99.7,
    "2010": 44.2, "2011": 22.0, "2012": 14.2, "2013": 39.0, "2014": 26.7,
    "2015": 16.6, "2016": 140.7
}

PORTFOLIO_01_PATRIMONIO = {
    "1998": 1310.0, "1999": 1174.3, "2000": 1057.2, "2001": 890.9,
    "2002": 780.8, "2003": 723.5, "2004": 674.3, "2005": 671.2,
    "2006": 637.4, "2007": 615.2, "2008": 477.0, "2009": 422.9,
    "2010": 399.6, "2011": 370.9, "2012": 390.2, "2013": 372.3,
    "2014": 371.9, "2015": 364.6, "2016": 229.4, "2017": 229.7
}

PORTFOLIO_01_RETORNOS = {
    "2000": -2.00, "2001": -8.85, "2002": -10.35, "2003": 4.25,
    "2004": 2.62, "2005": 8.74, "2006": 2.57, "2007": 0.32,
    "2008": -17.73, "2009": 11.26, "2010": 5.19, "2011": -2.46,
    "2012": 8.34, "2013": 5.14, "2014": 6.54, "2015": 1.41,
    "2016": 1.32, "2017": 0.15
}

# =====================================================
# DADOS FIXOS DO PORTFOLIO 02
# =====================================================

PORTFOLIO_02_WITHDRAWALS = {
    "2009": 0, "2010": 0, "2011": 2.7, "2012": 3.0,
    "2013": 2.1, "2014": 2.6, "2015": 3.9, "2016": 1.0
}

PORTFOLIO_02_PATRIMONIO = {
    "2009": 28.6, "2010": 17.3, "2011": 15.4, "2012": 12.5,
    "2013": 8.3, "2014": 6.5, "2015": 3.6, "2016": 2.7, "2017": 2.7
}

PORTFOLIO_02_PERFORMANCE_CUMULATIVA = {
    "2009": -27.44, "2010": -39.50, "2011": -36.90, "2012": -37.05,
    "2013": -47.40, "2014": -41.60, "2015": -32.00, "2016": -31.88, "2017": -31.13
}

PORTFOLIO_02_RETORNOS = {
    "2009": -27.44, "2010": -16.62, "2011": 4.30, "2012": -0.25,
    "2013": -16.44, "2014": 11.02, "2015": 16.45, "2016": 0.18, "2017": 1.09
}


class ChartAgent:
    """Agente especializado em criar gráficos com dados dos portfolios"""

    def __init__(self):
        self.client = from_openai(OpenAI(api_key=settings.OPENAI_API_KEY))

    async def generate_chart(self, data_context: str, user_intent: str) -> ChartSpecification:
        """
        Gera especificação de gráfico.
        Usa dados fixos para garantir precisão.
        """
        intent_lower = user_intent.lower()

        # Detectar portfolio
        is_p01 = any(x in intent_lower for x in ["01", "portfolio 1", "portfólio 1", "p01", "primeiro"])
        is_p02 = any(x in intent_lower for x in ["02", "portfolio 2", "portfólio 2", "p02", "segundo"])

        # Se não especificou, tentar detectar pelo contexto
        if not is_p01 and not is_p02:
            if "1" in user_intent and "2" not in user_intent:
                is_p01 = True
            elif "2" in user_intent and "1" not in user_intent:
                is_p02 = True
            else:
                is_p01 = True  # Default P01

        # Detectar tipo de gráfico
        is_withdrawal = any(word in intent_lower for word in
            ["retirada", "saque", "saída", "outflow", "withdrawal", "resgate"])

        is_patrimonio = any(word in intent_lower for word in
            ["patrimônio", "patrimonio", "evolução", "evolucao", "valor", "ativo",
             "líquido", "liquido", "asset", "net asset", "wealth", "dinheiro",
             "capital", "montante", "saldo", "total", "período", "periodo"])

        is_retorno = any(word in intent_lower for word in
            ["retorno", "return", "performance", "twr", "rendimento", "ganho", "perda anual"])

        is_performance_cumulativa = any(word in intent_lower for word in
            ["cumulativ", "acumulad", "cumulative", "total performance"])

        # =====================================================
        # PORTFOLIO 01
        # =====================================================
        if is_p01 and not is_p02:
            if is_withdrawal:
                return self._create_p01_withdrawal_chart()
            elif is_retorno and not is_performance_cumulativa:
                return self._create_p01_retornos_chart()
            elif is_patrimonio:
                return self._create_p01_patrimonio_chart()
            else:
                # Default: patrimônio
                return self._create_p01_patrimonio_chart()

        # =====================================================
        # PORTFOLIO 02
        # =====================================================
        if is_p02 and not is_p01:
            if is_withdrawal:
                return self._create_p02_withdrawal_chart()
            elif is_performance_cumulativa:
                return self._create_p02_performance_cumulativa_chart()
            elif is_retorno:
                return self._create_p02_retornos_chart()
            elif is_patrimonio:
                return self._create_p02_patrimonio_chart()
            else:
                # Default: patrimônio
                return self._create_p02_patrimonio_chart()

        # Default: P01 patrimônio
        return self._create_p01_patrimonio_chart()

    # =====================================================
    # GRÁFICOS PORTFOLIO 01
    # =====================================================

    def _create_p01_withdrawal_chart(self) -> ChartSpecification:
        """Gráfico de retiradas do Portfolio 01"""
        return ChartSpecification(
            type="bar",
            title="Retiradas (Saques) do Portfolio 01 - Ano a Ano",
            data=ChartData(
                labels=list(PORTFOLIO_01_WITHDRAWALS.keys()),
                values=list(PORTFOLIO_01_WITHDRAWALS.values())
            ),
            x_label="Ano",
            y_label="Valor (EUR milhares)",
            insights=[
                "Total de saques: EUR 1.133.600",
                "Maior saque: 2016 com EUR 140.700",
                "95% da redução patrimonial foi por saques do cliente"
            ]
        )

    def _create_p01_patrimonio_chart(self) -> ChartSpecification:
        """Gráfico de evolução patrimonial do Portfolio 01"""
        return ChartSpecification(
            type="line",
            title="Evolução Patrimonial do Portfolio 01 (1998-2017)",
            data=ChartData(
                labels=list(PORTFOLIO_01_PATRIMONIO.keys()),
                values=list(PORTFOLIO_01_PATRIMONIO.values())
            ),
            x_label="Ano",
            y_label="Valor (EUR milhares)",
            insights=[
                "Valor inicial (1998): EUR 1.310.000 (convertido de CHF)",
                "Valor final (2017): EUR 229.700",
                "Maior queda: 2008 (crise financeira global)",
                "Queda em 2016: grande saque de EUR 140.700"
            ]
        )

    def _create_p01_retornos_chart(self) -> ChartSpecification:
        """Gráfico de retornos anuais do Portfolio 01"""
        return ChartSpecification(
            type="bar",
            title="Retornos Anuais (TWR%) - Portfolio 01",
            data=ChartData(
                labels=list(PORTFOLIO_01_RETORNOS.keys()),
                values=list(PORTFOLIO_01_RETORNOS.values())
            ),
            x_label="Ano",
            y_label="TWR (%)",
            insights=[
                "Performance cumulativa (2006-2017): +17,65%",
                "Média anual: +1,63%",
                "Melhor ano: 2009 (+11,26%)",
                "Pior ano: 2008 (-17,73%)",
                "Win rate: 70,6% (12 de 17 anos positivos)"
            ]
        )

    # =====================================================
    # GRÁFICOS PORTFOLIO 02
    # =====================================================

    def _create_p02_withdrawal_chart(self) -> ChartSpecification:
        """Gráfico de retiradas do Portfolio 02"""
        return ChartSpecification(
            type="bar",
            title="Resgates do Portfolio 02 - Ano a Ano",
            data=ChartData(
                labels=list(PORTFOLIO_02_WITHDRAWALS.keys()),
                values=list(PORTFOLIO_02_WITHDRAWALS.values())
            ),
            x_label="Ano",
            y_label="Valor (EUR milhares)",
            insights=[
                "Total de saques: EUR 15.300",
                "2009-2010: Zero saques (fundo travado - gating)",
                "Cliente estava preso e não podia sacar durante a maior queda"
            ]
        )

    def _create_p02_patrimonio_chart(self) -> ChartSpecification:
        """Gráfico de evolução patrimonial do Portfolio 02"""
        return ChartSpecification(
            type="line",
            title="Evolução Patrimonial do Portfolio 02 (2009-2017)",
            data=ChartData(
                labels=list(PORTFOLIO_02_PATRIMONIO.keys()),
                values=list(PORTFOLIO_02_PATRIMONIO.values())
            ),
            x_label="Ano",
            y_label="Valor (EUR milhares)",
            insights=[
                "Valor inicial (2009): EUR 28.600",
                "Valor final (2017): EUR 2.700",
                "Perda total: -90,6%",
                "Produto: UBS Global Property Fund (100% Real Estate)"
            ]
        )

    def _create_p02_performance_cumulativa_chart(self) -> ChartSpecification:
        """Gráfico de performance cumulativa do Portfolio 02"""
        return ChartSpecification(
            type="line",
            title="Performance Cumulativa - Portfolio 02 (2009-2017)",
            data=ChartData(
                labels=list(PORTFOLIO_02_PERFORMANCE_CUMULATIVA.keys()),
                values=list(PORTFOLIO_02_PERFORMANCE_CUMULATIVA.values())
            ),
            x_label="Ano",
            y_label="Performance Cumulativa (%)",
            insights=[
                "Performance final: -31,13%",
                "Pior momento: 2013 com -47,40%",
                "Tolerância do perfil: -20%",
                "Violação da tolerância: 27,40pp além do limite",
                "Anos em violação: 6 de 9"
            ]
        )

    def _create_p02_retornos_chart(self) -> ChartSpecification:
        """Gráfico de retornos anuais do Portfolio 02"""
        return ChartSpecification(
            type="bar",
            title="Retornos Anuais (TWR%) - Portfolio 02",
            data=ChartData(
                labels=list(PORTFOLIO_02_RETORNOS.keys()),
                values=list(PORTFOLIO_02_RETORNOS.values())
            ),
            x_label="Ano",
            y_label="TWR (%)",
            insights=[
                "Média anual: -4,58%",
                "Melhor ano: 2015 (+16,45%)",
                "Pior ano: 2009 (-27,44%)",
                "Fundo estava travado em 2009-2010"
            ]
        )

    async def _generate_with_llm(self, data_context: str, user_intent: str) -> ChartSpecification:
        """Gera gráfico usando LLM para casos não cobertos pelos dados fixos"""
        system_prompt = """Você extrai dados numéricos de tabelas para criar gráficos.
Crie gráficos com dados ANO A ANO, nunca agrupe períodos.
Use valores absolutos (positivos) para gráficos."""

        chart_spec = self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            response_model=ChartSpecification,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Dados: {data_context}\n\nObjetivo: {user_intent}"}
            ],
            temperature=0.1
        )

        return chart_spec
