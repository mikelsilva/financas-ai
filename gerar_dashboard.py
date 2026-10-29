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
from financas_ai.core import categorizador

CSV = Path("dados/meus_dados.csv")
TEMPLATE = Path("dashboard.html")
SAIDA = Path("dashboard_local.html")


def main() -> None:
    if not CSV.exists():
        print(f"❌ {CSV} não encontrado. Rode antes: python rodar_pluggy.py")
        sys.exit(1)

    df = pd.read_csv(CSV, parse_dates=["data"])
    df = df.dropna(subset=["data"])

    bancos = sorted(df["banco"].dropna().unique().tolist())
    # transações cruas: o dashboard calcula tudo (filtros por fonte e mês) no navegador
    transacoes = [
        {
            "d": r["data"].strftime("%Y-%m-%d"),
            "desc": str(r["descricao"])[:60],
            "v": round(float(r["valor"]), 2),
            "banco": str(r["banco"]),
            "conta": str(r["conta"]),
            "cat": (str(r["categoria"]) if pd.notna(r["categoria"]) else "Outros"),
        }
        for _, r in df.iterrows()
    ]
    dados = {
        "meta": {
            "exemplo": False,
            "subtitle": "Consolidador pessoal via Open Finance · " + " · ".join(bancos),
        },
        "transacoes": transacoes,
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
    cob = categorizador.cobertura(df)
    print(f"✅ Dashboard gerado: {SAIDA.resolve()}")
    print(f"   {len(transacoes)} transações · {len(bancos)} fonte(s) · cobertura {cob}%")
    print("   Abra no navegador:  start dashboard_local.html")


if __name__ == "__main__":
    main()
