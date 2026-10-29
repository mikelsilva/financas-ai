"""Gera o dashboard com SEUS dados reais (local, nada sai da máquina).

Lê dados/meus_dados.csv (criado pelo rodar_pluggy.py / rodar_arquivo.py),
calcula as análises e injeta no template dashboard.html, gerando
dashboard_local.html — que você abre no navegador.

Uso:
    python gerar_dashboard.py

O dashboard_local.html contém seus números reais, por isso é ignorado pelo Git.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import pandas as pd
from financas_ai.core import analise, categorizador

CSV = Path("dados/meus_dados.csv")
TEMPLATE = Path("dashboard.html")
SAIDA = Path("dashboard_local.html")


def main() -> None:
    if not CSV.exists():
        print(f"❌ {CSV} não encontrado. Rode antes: python rodar_pluggy.py")
        sys.exit(1)

    df = pd.read_csv(CSV, parse_dates=["data"])

    cat = analise.gastos_por_categoria(df)
    em = analise.evolucao_mensal(df)
    rec = analise.possiveis_recorrencias(df).head(6)

    dados = {
        "kpis": {
            "transacoes": int(len(df)),
            "bancos": sorted(df["banco"].dropna().unique().tolist()),
            "cobertura": categorizador.cobertura(df),
            "total_saidas": round(float(df[df["valor"] < 0]["valor"].sum()) * -1, 2),
            "total_entradas": round(float(df[df["valor"] > 0]["valor"].sum()), 2),
        },
        "categorias": [{"nome": k, "valor": round(float(v), 2)} for k, v in cat.items()],
        "meses": [{"mes": i, "entradas": round(float(r.entradas), 2),
                   "saidas": round(float(r.saidas), 2), "saldo": round(float(r.saldo), 2)}
                  for i, r in em.iterrows()],
        "recorrencias": [{"nome": str(r["exemplo"])[:32], "valor": round(abs(float(r["valor_medio"])), 2),
                          "meses": int(r["ocorrencias"])} for _, r in rec.iterrows()],
    }

    html = TEMPLATE.read_text(encoding="utf-8")
    novo = "const DADOS = /*DADOS_INICIO*/" + json.dumps(dados, ensure_ascii=False) + "/*DADOS_FIM*/"
    html, n = re.subn(
        r"const DADOS = /\*DADOS_INICIO\*/.*?/\*DADOS_FIM\*/",
        lambda _m: novo, html, count=1, flags=re.DOTALL,
    )
    if n == 0:
        print("❌ Não achei o marcador de dados no template dashboard.html.")
        sys.exit(1)

    SAIDA.write_text(html, encoding="utf-8")
    print(f"✅ Dashboard gerado: {SAIDA.resolve()}")
    print(f"   {dados['kpis']['transacoes']} transações · cobertura {dados['kpis']['cobertura']}%")
    print("   Abra o arquivo no navegador (dê dois cliques ou arraste pra uma aba).")


if __name__ == "__main__":
    main()
