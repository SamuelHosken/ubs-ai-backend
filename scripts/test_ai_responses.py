#!/usr/bin/env python3
"""
Script de Teste Automatizado da IA
Envia perguntas e coleta respostas para avaliação manual.
"""

import httpx
import json
import asyncio
from datetime import datetime
from pathlib import Path

# Configurações
BASE_URL = "https://ubs-ai-backend-production.up.railway.app"
EMAIL = "dev@ubs.com"
PASSWORD = "dev123"

# 45 Perguntas organizadas em 9 categorias
PERGUNTAS = [
    # CATEGORIA 1: VALORES E EVOLUÇÃO (8 perguntas)
    {"id": "1.1", "categoria": "Valores e Evolução", "pergunta": "Qual foi o valor máximo que meu portfolio teve?",
     "pontos_chave": ["2.034.713", "1998", "pico", "máximo"]},
    {"id": "1.2", "categoria": "Valores e Evolução", "pergunta": "Quanto sobrou no final de 2017?",
     "pontos_chave": ["3.312", "2017", "liquidação", "final"]},
    {"id": "1.3", "categoria": "Valores e Evolução", "pergunta": "De quanto para quanto foi meu patrimônio?",
     "pontos_chave": ["99", "queda", "saques", "1.2"]},
    {"id": "1.4", "categoria": "Valores e Evolução", "pergunta": "Quanto eu perdi na crise de 2008?",
     "pontos_chave": ["17,73", "2008", "lehman", "crise"]},
    {"id": "1.5", "categoria": "Valores e Evolução", "pergunta": "Quanto eu tinha em janeiro de 2017?",
     "pontos_chave": ["229.711", "229", "janeiro", "2017"]},
    {"id": "1.6", "categoria": "Valores e Evolução", "pergunta": "Quanto eu tinha no final de 2008?",
     "pontos_chave": ["477.029", "477", "dezembro", "2008"]},
    {"id": "1.7", "categoria": "Valores e Evolução", "pergunta": "Por que meu patrimônio caiu tanto?",
     "pontos_chave": ["95%", "saques", "cliente", "não foi perda"]},
    {"id": "1.8", "categoria": "Valores e Evolução", "pergunta": "Qual foi o valor máximo em euros?",
     "pontos_chave": ["1.251", "agosto", "2000", "pico"]},

    # CATEGORIA 2: MOEDAS (5 perguntas)
    {"id": "2.1", "categoria": "Moedas", "pergunta": "O que era DEM nos meus extratos?",
     "pontos_chave": ["marco", "alemão", "alemanha", "2002"]},
    {"id": "2.2", "categoria": "Moedas", "pergunta": "O que era XEU?",
     "pontos_chave": ["ecu", "euro", "1999", "predecessor"]},
    {"id": "2.3", "categoria": "Moedas", "pergunta": "Em quais moedas meu dinheiro estava em 1998?",
     "pontos_chave": ["chf", "61%", "dem", "xeu"]},
    {"id": "2.4", "categoria": "Moedas", "pergunta": "Em quais moedas meu dinheiro está agora?",
     "pontos_chave": ["eur", "84%", "usd", "10%"]},
    {"id": "2.5", "categoria": "Moedas", "pergunta": "Quando meu portfolio passou a ser em Euro?",
     "pontos_chave": ["1999", "euro", "conversão"]},

    # CATEGORIA 3: ALOCAÇÃO (5 perguntas)
    {"id": "3.1", "categoria": "Alocação", "pergunta": "Como meu dinheiro está dividido por tipo de investimento?",
     "pontos_chave": ["bonds", "50%", "equities", "24%", "hedge"]},
    {"id": "3.2", "categoria": "Alocação", "pergunta": "Quando começaram os investimentos alternativos?",
     "pontos_chave": ["2003", "hedge", "alternative", "20%"]},
    {"id": "3.3", "categoria": "Alocação", "pergunta": "Quando o fundo imobiliário entrou no portfolio?",
     "pontos_chave": ["2005", "property", "imobiliário", "real estate"]},
    {"id": "3.4", "categoria": "Alocação", "pergunta": "Quantas cotas do fundo imobiliário eu tinha?",
     "pontos_chave": ["2.815", "157", "cotas"]},
    {"id": "3.5", "categoria": "Alocação", "pergunta": "Quanto o fundo imobiliário perdeu?",
     "pontos_chave": ["35%", "34%", "10,64", "6,92"]},

    # CATEGORIA 4: TRANSAÇÕES (5 perguntas)
    {"id": "4.1", "categoria": "Transações", "pergunta": "Qual foi o maior depósito que eu fiz?",
     "pontos_chave": ["126.432", "maio", "2000", "depósito"]},
    {"id": "4.2", "categoria": "Transações", "pergunta": "Qual foi o maior saque em um ano?",
     "pontos_chave": ["256.400", "2000", "maior", "saque"]},
    {"id": "4.3", "categoria": "Transações", "pergunta": "Quanto eu saquei em 2016?",
     "pontos_chave": ["140.700", "2016"]},
    {"id": "4.4", "categoria": "Transações", "pergunta": "Quanto eu saquei no total?",
     "pontos_chave": ["1.148", "1.133", "total", "saques"]},
    {"id": "4.5", "categoria": "Transações", "pergunta": "Quanto eu sacava por mês normalmente?",
     "pontos_chave": ["6.000", "10.000", "mensal"]},

    # CATEGORIA 5: PERFORMANCE (6 perguntas)
    {"id": "5.1", "categoria": "Performance", "pergunta": "Qual foi o melhor ano de performance?",
     "pontos_chave": ["2009", "11,26", "melhor"]},
    {"id": "5.2", "categoria": "Performance", "pergunta": "Qual foi o pior ano de performance?",
     "pontos_chave": ["2008", "17,73", "pior"]},
    {"id": "5.3", "categoria": "Performance", "pergunta": "Qual foi a performance total do Portfolio 01?",
     "pontos_chave": ["17,65", "positiv", "cumulativ"]},
    {"id": "5.4", "categoria": "Performance", "pergunta": "Quanto o portfolio perdeu no último trimestre de 2008?",
     "pontos_chave": ["q4", "8,78", "trimestre", "outubro"]},
    {"id": "5.5", "categoria": "Performance", "pergunta": "Quantos anos foram positivos vs negativos?",
     "pontos_chave": ["12", "positivo", "70%", "5"]},
    {"id": "5.6", "categoria": "Performance", "pergunta": "Quando o portfolio recuperou as perdas de 2008?",
     "pontos_chave": ["2012", "recuperou", "positivo"]},

    # CATEGORIA 6: AÇÕES E FUNDOS (4 perguntas)
    {"id": "6.1", "categoria": "Ações e Fundos", "pergunta": "Quais ações individuais eu tinha em 1998?",
     "pontos_chave": ["roche", "ubs", "credit suisse", "novartis"]},
    {"id": "6.2", "categoria": "Ações e Fundos", "pergunta": "Qual foi a melhor ação que eu tive?",
     "pontos_chave": ["roche", "571", "melhor"]},
    {"id": "6.3", "categoria": "Ações e Fundos", "pergunta": "Quais hedge funds eu tinha?",
     "pontos_chave": ["multi-strategy", "quellos", "hedge", "alternative"]},
    {"id": "6.4", "categoria": "Ações e Fundos", "pergunta": "O que aconteceu com o fundo imobiliário em 2008?",
     "pontos_chave": ["gating", "congelado", "dezembro", "2008"]},

    # CATEGORIA 7: ESTRATÉGIA E PERFIL (4 perguntas)
    {"id": "7.1", "categoria": "Estratégia e Perfil", "pergunta": "Qual era meu perfil de investidor?",
     "pontos_chave": ["c", "yield", "conservador", "20%"]},
    {"id": "7.2", "categoria": "Estratégia e Perfil", "pergunta": "O que significa perfil 'C Yield'?",
     "pontos_chave": ["moderado", "20%", "4 anos", "conservador"]},
    {"id": "7.3", "categoria": "Estratégia e Perfil", "pergunta": "Minha estratégia mudou ao longo do tempo?",
     "pontos_chave": ["balanced", "yield", "mudou", "2005"]},
    {"id": "7.4", "categoria": "Estratégia e Perfil", "pergunta": "O banco respeitou meu perfil de risco?",
     "pontos_chave": ["violação", "47", "não respeitou", "20%"]},

    # CATEGORIA 8: ASSESSOR E CUSTOS (3 perguntas)
    {"id": "8.1", "categoria": "Assessor e Custos", "pergunta": "Quem era meu assessor no UBS?",
     "pontos_chave": ["philippe", "poisson", "crans"]},
    {"id": "8.2", "categoria": "Assessor e Custos", "pergunta": "Em qual agência minha conta estava?",
     "pontos_chave": ["crans", "sierre", "zürich", "montana"]},
    {"id": "8.3", "categoria": "Assessor e Custos", "pergunta": "Quanto o banco cobrava de taxa nos hedge funds?",
     "pontos_chave": ["0,65", "2,30", "taxa", "%"]},

    # CATEGORIA 9: PORTFOLIO 02 ESPECÍFICO (5 perguntas)
    {"id": "9.1", "categoria": "Portfolio 02", "pergunta": "O que é o Portfolio 02?",
     "pontos_chave": ["property", "imobiliário", "ilíquido", "fundo"]},
    {"id": "9.2", "categoria": "Portfolio 02", "pergunta": "Quanto o Portfolio 02 perdeu?",
     "pontos_chave": ["31", "47", "perda"]},
    {"id": "9.3", "categoria": "Portfolio 02", "pergunta": "Quanto sobrou no Portfolio 02?",
     "pontos_chave": ["1.088", "2.692", "final"]},
    {"id": "9.4", "categoria": "Portfolio 02", "pergunta": "Quais foram os problemas do Portfolio 02?",
     "pontos_chave": ["gating", "violação", "negligência", "3 meses"]},
    {"id": "9.5", "categoria": "Portfolio 02", "pergunta": "De quem é a culpa pelas perdas do P02?",
     "pontos_chave": ["90%", "ubs", "0%", "cliente"]},
]


async def login(client: httpx.AsyncClient) -> str:
    """Faz login e retorna o token JWT"""
    print(f"\n🔐 Fazendo login como {EMAIL}...")

    response = await client.post(
        f"{BASE_URL}/auth/login",
        data={"username": EMAIL, "password": PASSWORD}
    )

    if response.status_code != 200:
        raise Exception(f"Erro no login: {response.status_code} - {response.text}")

    token = response.json()["access_token"]
    print("✅ Login bem-sucedido!")
    return token


async def send_question(client: httpx.AsyncClient, token: str, pergunta: str) -> dict:
    """Envia uma pergunta e retorna a resposta"""
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        f"{BASE_URL}/chat/",
        json={"message": pergunta, "conversation_history": []},
        headers=headers,
        timeout=120.0
    )

    if response.status_code != 200:
        return {
            "error": True,
            "status_code": response.status_code,
            "message": response.text
        }

    return response.json()


def check_pontos_chave(resposta: str, pontos_chave: list) -> dict:
    """Verifica quantos pontos-chave estão presentes na resposta"""
    resposta_lower = resposta.lower()

    encontrados = []
    nao_encontrados = []

    for ponto in pontos_chave:
        if ponto.lower() in resposta_lower:
            encontrados.append(ponto)
        else:
            nao_encontrados.append(ponto)

    return {
        "total": len(pontos_chave),
        "encontrados": len(encontrados),
        "lista_encontrados": encontrados,
        "lista_nao_encontrados": nao_encontrados,
        "percentual": round(len(encontrados) / len(pontos_chave) * 100, 1) if pontos_chave else 0
    }


async def run_tests():
    """Executa todos os testes"""
    resultados = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    async with httpx.AsyncClient() as client:
        try:
            token = await login(client)
        except Exception as e:
            print(f"\n❌ Falha no login: {e}")
            return

        print(f"\n📝 Iniciando testes com {len(PERGUNTAS)} perguntas...\n")
        print("=" * 60)

        # Agrupar por categoria para relatório
        categorias_stats = {}

        for i, item in enumerate(PERGUNTAS, 1):
            cat = item['categoria']
            print(f"\n[{i}/{len(PERGUNTAS)}] {cat}")
            print(f"    Pergunta {item['id']}: {item['pergunta'][:50]}...")

            try:
                resposta = await send_question(client, token, item["pergunta"])

                if resposta.get("error"):
                    print(f"    ❌ Erro: {resposta['message'][:100]}")
                    resultado = {
                        "id": item["id"],
                        "categoria": cat,
                        "pergunta": item["pergunta"],
                        "status": "ERRO",
                        "erro": resposta["message"],
                        "resposta": None,
                        "pontos_chave": None
                    }
                else:
                    resposta_texto = resposta.get("response", "")
                    verificacao = check_pontos_chave(resposta_texto, item["pontos_chave"])

                    status_icon = "✅" if verificacao["percentual"] >= 70 else "⚠️" if verificacao["percentual"] >= 50 else "❌"
                    print(f"    {status_icon} Pontos-chave: {verificacao['encontrados']}/{verificacao['total']} ({verificacao['percentual']}%)")

                    # Atualizar stats da categoria
                    if cat not in categorias_stats:
                        categorias_stats[cat] = {"total": 0, "soma": 0}
                    categorias_stats[cat]["total"] += 1
                    categorias_stats[cat]["soma"] += verificacao["percentual"]

                    resultado = {
                        "id": item["id"],
                        "categoria": cat,
                        "pergunta": item["pergunta"],
                        "status": "OK",
                        "resposta": resposta_texto,
                        "chart": resposta.get("chart"),
                        "agents_used": resposta.get("agents_used"),
                        "pontos_chave": verificacao
                    }

                resultados.append(resultado)

            except Exception as e:
                print(f"    ❌ Exceção: {str(e)[:100]}")
                resultados.append({
                    "id": item["id"],
                    "categoria": cat,
                    "pergunta": item["pergunta"],
                    "status": "EXCEÇÃO",
                    "erro": str(e),
                    "resposta": None,
                    "pontos_chave": None
                })

            await asyncio.sleep(1)

    # Salvar resultados
    output_dir = Path(__file__).parent.parent.parent
    output_file = output_dir / f"RESULTADO_TESTE_IA_{timestamp}.json"
    output_md = output_dir / f"RESULTADO_TESTE_IA_{timestamp}.md"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    gerar_relatorio_md(resultados, output_md, categorias_stats)

    print("\n" + "=" * 60)
    print(f"\n✅ Testes concluídos!")
    print(f"   📄 JSON: {output_file}")
    print(f"   📄 Relatório: {output_md}")

    # Resumo por categoria
    print(f"\n📊 RESUMO POR CATEGORIA:")
    for cat, stats in sorted(categorias_stats.items()):
        media = stats["soma"] / stats["total"] if stats["total"] > 0 else 0
        icon = "✅" if media >= 70 else "⚠️" if media >= 50 else "❌"
        print(f"   {icon} {cat}: {media:.1f}%")

    # Resumo geral
    ok_count = sum(1 for r in resultados if r["status"] == "OK")
    if ok_count > 0:
        media_geral = sum(
            r["pontos_chave"]["percentual"]
            for r in resultados
            if r["status"] == "OK" and r["pontos_chave"]
        ) / ok_count
    else:
        media_geral = 0

    print(f"\n📈 MÉDIA GERAL: {media_geral:.1f}%")
    meta = "✅ META ATINGIDA!" if media_geral >= 70 else "❌ Abaixo da meta de 70%"
    print(f"   {meta}")


def gerar_relatorio_md(resultados: list, output_path: Path, categorias_stats: dict):
    """Gera relatório em Markdown"""
    md = []
    md.append("# Resultado do Teste da IA - Base de Conhecimento")
    md.append(f"\n**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append(f"**Total de perguntas:** {len(resultados)}")

    # Resumo por categoria
    md.append("\n## Resumo por Categoria")
    md.append("\n| Categoria | Média | Status |")
    md.append("|-----------|-------|--------|")
    for cat, stats in sorted(categorias_stats.items()):
        media = stats["soma"] / stats["total"] if stats["total"] > 0 else 0
        status = "✅" if media >= 70 else "⚠️" if media >= 50 else "❌"
        md.append(f"| {cat} | {media:.1f}% | {status} |")

    # Média geral
    ok_count = sum(1 for r in resultados if r["status"] == "OK")
    if ok_count > 0:
        media_geral = sum(
            r["pontos_chave"]["percentual"]
            for r in resultados
            if r["status"] == "OK" and r["pontos_chave"]
        ) / ok_count
    else:
        media_geral = 0

    md.append(f"\n**Média Geral: {media_geral:.1f}%**")
    md.append(f"**Meta: 70%** {'✅ ATINGIDA' if media_geral >= 70 else '❌ NÃO ATINGIDA'}")

    md.append("\n---\n")

    # Resultados detalhados
    categorias = {}
    for r in resultados:
        cat = r["categoria"]
        if cat not in categorias:
            categorias[cat] = []
        categorias[cat].append(r)

    for categoria, items in categorias.items():
        md.append(f"\n## {categoria}\n")

        for r in items:
            md.append(f"### Pergunta {r['id']}")
            md.append(f"**Pergunta:** {r['pergunta']}\n")

            if r["status"] != "OK":
                md.append(f"**Status:** ❌ {r['status']}")
                continue

            pc = r.get("pontos_chave", {})
            if pc:
                icon = "✅" if pc["percentual"] >= 70 else "⚠️" if pc["percentual"] >= 50 else "❌"
                md.append(f"**Pontos-chave:** {icon} {pc['encontrados']}/{pc['total']} ({pc['percentual']}%)")
                if pc.get("lista_nao_encontrados"):
                    md.append(f"- Não encontrados: {', '.join(pc['lista_nao_encontrados'])}")

            md.append("\n**Resposta:**")
            md.append("```")
            md.append(r.get("resposta", "N/A")[:1500])
            if len(r.get("resposta", "")) > 1500:
                md.append("... [truncado]")
            md.append("```\n")
            md.append("---\n")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))


if __name__ == "__main__":
    print("=" * 60)
    print("   TESTE DA BASE DE CONHECIMENTO - 45 Perguntas")
    print("=" * 60)

    asyncio.run(run_tests())
