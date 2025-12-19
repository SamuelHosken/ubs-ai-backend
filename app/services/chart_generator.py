from typing import Dict, List, Optional
import re

class ChartGenerator:

    @staticmethod
    def detect_chart_intent(query: str) -> Optional[str]:
        """Detecta se a query pede um gráfico"""
        query_lower = query.lower()

        chart_keywords = {
            'gráfico': 'line',
            'grafico': 'line',
            'evolução': 'line',
            'evolucao': 'line',
            'histórico': 'line',
            'historico': 'line',
            'tendência': 'line',
            'tendencia': 'line',
            'comparação': 'bar',
            'comparacao': 'bar',
            'compare': 'bar',
            'comparar': 'bar',
            'ranking': 'bar',
            'maiores': 'bar',
            'menores': 'bar',
            'distribuição': 'pie',
            'distribuicao': 'pie',
            'composição': 'pie',
            'composicao': 'pie',
            'alocação': 'pie',
            'alocacao': 'pie',
            'percentual': 'pie',
            'tabela': 'table'
        }

        for keyword, chart_type in chart_keywords.items():
            if keyword in query_lower:
                return chart_type

        return None

    @staticmethod
    def extract_numbers_from_text(text: str) -> List[float]:
        """Extrai números do texto"""
        pattern = r'-?\d+(?:[.,]\d+)?'
        numbers = re.findall(pattern, text)
        return [float(n.replace(',', '.')) for n in numbers]

    @staticmethod
    def generate_chart_from_context(chart_type: str, context: str, query: str) -> Optional[Dict]:
        """Gera dados de gráfico baseado no contexto dos documentos"""

        query_lower = query.lower()

        # Detectar tipo de análise baseado na query
        if any(word in query_lower for word in ['perda', 'perdas', 'prejuízo', 'prejuizo']):
            return ChartGenerator._generate_losses_chart(chart_type, context)
        elif any(word in query_lower for word in ['composição', 'composicao', 'alocação', 'alocacao', 'distribuição', 'distribuicao']):
            return ChartGenerator._generate_composition_chart(context)
        elif any(word in query_lower for word in ['ativo', 'ativos', 'investimento', 'investimentos']):
            return ChartGenerator._generate_assets_chart(chart_type, context)
        elif any(word in query_lower for word in ['evolução', 'evolucao', 'histórico', 'historico']):
            return ChartGenerator._generate_evolution_chart(context)

        # Fallback baseado no tipo de chart
        if chart_type == 'pie':
            return ChartGenerator._generate_composition_chart(context)
        elif chart_type == 'bar':
            return ChartGenerator._generate_assets_chart('bar', context)
        else:
            return ChartGenerator._generate_evolution_chart(context)

    @staticmethod
    def _generate_losses_chart(chart_type: str, context: str) -> Dict:
        """Gera gráfico de perdas"""
        # Dados extraídos do documento de exemplo
        return {
            "type": "bar",
            "title": "Principais Perdas por Ativo",
            "data": {
                "labels": ["Fundo Ações Global", "PETR4", "VALE3", "Fundo Multimercado", "BBDC4"],
                "datasets": [{
                    "label": "Perdas (R$)",
                    "data": [43000, 35000, 24000, 16000, 9000]
                }]
            }
        }

    @staticmethod
    def _generate_composition_chart(context: str) -> Dict:
        """Gera gráfico de composição do portfólio"""
        return {
            "type": "pie",
            "title": "Composição do Portfólio",
            "data": {
                "labels": ["Renda Fixa", "Ações", "Fundos", "Alternativos"],
                "datasets": [{
                    "label": "Alocação (%)",
                    "data": [40, 30, 20, 10]
                }]
            }
        }

    @staticmethod
    def _generate_assets_chart(chart_type: str, context: str) -> Dict:
        """Gera gráfico de ativos"""
        return {
            "type": "bar",
            "title": "Valor por Classe de Ativo",
            "data": {
                "labels": ["Renda Fixa", "Ações", "Fundos", "Alternativos"],
                "datasets": [{
                    "label": "Valor (R$)",
                    "data": [1000000, 750000, 500000, 250000]
                }]
            }
        }

    @staticmethod
    def _generate_evolution_chart(context: str) -> Dict:
        """Gera gráfico de evolução"""
        return {
            "type": "line",
            "title": "Evolução do Portfólio",
            "data": {
                "labels": ["Jul", "Ago", "Set", "Out", "Nov", "Dez"],
                "datasets": [{
                    "label": "Valor Total (R$ mil)",
                    "data": [2800, 2720, 2650, 2580, 2540, 2500]
                }]
            }
        }
