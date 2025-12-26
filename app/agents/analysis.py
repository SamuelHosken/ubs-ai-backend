from openai import OpenAI
from instructor import from_openai
from pydantic import BaseModel, Field
from typing import List
from app.core.config import settings

class FinancialAnalysis(BaseModel):
    summary: str = Field(description="Resumo em 2-3 frases")
    key_findings: List[str] = Field(description="3-5 descobertas principais")
    total_amount: float = Field(default=0)
    confidence: float = Field(ge=0, le=1)
    sources: List[str]
    recommendation: str

class AnalysisAgent:
    SYSTEM_PROMPT = """Voce e analista financeiro especializado em portfolios UBS.

REGRAS:
1. Use APENAS dados dos documentos
2. Cite numeros com fonte
3. Se nao souber, diga "Nao encontrei"
4. Seja preciso e conservador"""

    def __init__(self):
        self.client = from_openai(OpenAI(api_key=settings.OPENAI_API_KEY))

    async def analyze(self, context: str, question: str) -> FinancialAnalysis:
        analysis = self.client.chat.completions.create(
            model="gpt-4.1",
            response_model=FinancialAnalysis,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Contexto:\n{context}\n\nPergunta:\n{question}"
                }
            ],
            temperature=0.1
        )

        return analysis
