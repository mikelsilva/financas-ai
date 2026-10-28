"""Demonstracao ponta a ponta.

Gera os dados de exemplo, consolida os tres bancos e responde algumas das
perguntas que o Pierre responde -- tudo local, sem API paga.

    python demo.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from financas_ai import pipeline                       # noqa: E402
from financas_ai.core import analise, categorizador    # noqa: E402
import dados.gerar_exemplos as gen                      # noqa: E402


def real(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def main() -> None:
    # 1) garante os arquivos de exemplo
    nu = gen.gerar_nubank_conta()
    c6 = gen.gerar_c6_ofx()
    rico = gen.gerar_rico_csv()

    # 2) consolida os tres bancos numa tabela so
    df = pipeline.consolidar({"nubank": nu, "c6": c6, "rico": rico})

    print("=" * 60)
    print(f"Transacoes consolidadas: {len(df)}  (bancos: {sorted(df['banco'].unique())})")
    print(f"Cobertura do categorizador: {categorizador.cobertura(df)}%")
    print("=" * 60)

    print("\n>> Gastos por categoria (todo o periodo):")
    for cat, val in analise.gastos_por_categoria(df).items():
        print(f"   {cat:16} {real(val)}")

    print("\n>> Evolucao mensal (entradas / saidas / saldo):")
    print(analise.evolucao_mensal(df).apply(lambda c: c.map(real)).to_string())

    print("\n>> 5 maiores gastos:")
    for _, r in analise.maiores_gastos(df, n=5).iterrows():
        print(f"   {r['data']:%d/%m} {r['descricao'][:34]:34} {real(r['valor'])}  [{r['categoria']}]")

    print("\n>> Possiveis cobrancas recorrentes (assinaturas):")
    rec = analise.possiveis_recorrencias(df)
    for chave, r in rec.head(6).iterrows():
        print(f"   {r['exemplo'][:34]:34} ~{real(r['valor_medio'])}/mes  ({r['ocorrencias']} meses)")

    # exemplo de "pergunta" respondida direto
    print("\n>> Pergunta: quanto gastei com Delivery no total?")
    print(f"   {real(analise.total_categoria(df, 'Delivery'))}")


if __name__ == "__main__":
    main()
