"""Runner LOCAL a partir de um extrato exportado (CSV ou OFX).

Caminho confiavel: em vez de brigar com a API nao-oficial do Nubank (que
bloqueia com 403), use o extrato que o proprio banco exporta. Funciona com
Nubank, C6 e qualquer banco que exporte OFX.

Uso:
    python rodar_arquivo.py caminho/do/extrato.ofx
    python rodar_arquivo.py extrato_nubank.csv

Detecta o formato pela extensao e monta as mesmas analises do projeto.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import pandas as pd
from financas_ai.conectores import nubank, ofx
from financas_ai.core import schema, categorizador, analise


def real(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def ler_arquivo(caminho: str) -> pd.DataFrame:
    p = Path(caminho)
    if not p.exists():
        print(f"❌ Arquivo não encontrado: {p}")
        sys.exit(1)

    ext = p.suffix.lower()
    if ext == ".ofx":
        trans = ofx.ler_transacoes(p)
        if not trans:
            print("❌ Nenhuma transação encontrada no OFX.")
            sys.exit(1)
        df = pd.DataFrame(trans)
        df["banco"] = "nubank"
        df["conta"] = "extrato"
        df["categoria"] = pd.NA
        return schema.validar(df)
    elif ext == ".csv":
        # tenta o conector do Nubank (cobre extrato de conta e fatura do cartao)
        try:
            return nubank.ler(p)
        except Exception as e:
            print(f"❌ Não reconheci o CSV: {e}")
            print("Se for de outro banco, me avise o formato que eu adapto.")
            sys.exit(1)
    else:
        print(f"❌ Formato não suportado: {ext}. Use .ofx ou .csv")
        sys.exit(1)


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python rodar_arquivo.py caminho/do/extrato.ofx")
        sys.exit(1)

    df = ler_arquivo(sys.argv[1])
    df = categorizador.categorizar(df)

    Path("dados").mkdir(exist_ok=True)
    df.to_csv("dados/meus_dados.csv", index=False)

    print("=" * 56)
    print(f"✅ {len(df)} transações carregadas de {Path(sys.argv[1]).name}")
    print(f"   Cobertura do categorizador: {categorizador.cobertura(df)}%")
    print("=" * 56)

    print("\n>> Seus gastos por categoria:")
    for cat, val in analise.gastos_por_categoria(df).items():
        print(f"   {cat:16} {real(val)}")

    print("\n>> Evolução mensal (entradas / saídas / saldo):")
    em = analise.evolucao_mensal(df)
    if len(em):
        print(em.apply(lambda c: c.map(real)).to_string())

    rec = analise.possiveis_recorrencias(df)
    if len(rec):
        print("\n>> Possíveis cobranças recorrentes:")
        for _, r in rec.head(8).iterrows():
            print(f"   {r['exemplo'][:34]:34} ~{real(abs(r['valor_medio']))}/mês ({r['ocorrencias']} meses)")

    print("\nDados salvos em dados/meus_dados.csv (não vai pro GitHub).")


if __name__ == "__main__":
    main()
