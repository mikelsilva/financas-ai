"""Runner LOCAL do conector Pluggy (Open Finance via Meu Pluggy).

Open Finance real, automático e gratuito para uso pessoal — sem engenharia
reversa, sem 403. Rode na SUA máquina.

Antes de rodar:
  1. Conecte suas contas em https://meu.pluggy.ai
  2. No dashboard.pluggy.ai: crie uma aplicação, ative o conector "MeuPluggy",
     e copie o Client ID, o Client Secret e o Item ID (da conexão criada).
  3. Defina as variáveis de ambiente (PowerShell):
       $env:PLUGGY_CLIENT_ID="seu-client-id"
       $env:PLUGGY_CLIENT_SECRET="seu-client-secret"
       $env:PLUGGY_ITEM_ID="seu-item-id"

Uso:
    python rodar_pluggy.py
    python rodar_pluggy.py ITEM_ID_1 ITEM_ID_2     # vários itens
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from financas_ai.conectores import pluggy
from financas_ai.core import categorizador, analise


def real(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def main() -> None:
    itens = sys.argv[1:] or ([os.environ["PLUGGY_ITEM_ID"]]
                             if os.environ.get("PLUGGY_ITEM_ID") else [])
    if not itens:
        print("❌ Informe o Item ID: defina PLUGGY_ITEM_ID ou passe como argumento.")
        print("   Ex.: python rodar_pluggy.py 1a2b3c4d-....")
        sys.exit(1)

    try:
        df = pluggy.ler(itens)
    except Exception as e:
        print(f"❌ Não consegui ler da Pluggy: {e}")
        print("Confira as variáveis PLUGGY_CLIENT_ID / PLUGGY_CLIENT_SECRET e o Item ID.")
        sys.exit(1)

    df = categorizador.categorizar(df)

    Path("dados").mkdir(exist_ok=True)
    df.to_csv("dados/meus_dados.csv", index=False)

    print("=" * 56)
    print(f"✅ {len(df)} transações lidas via Open Finance (Pluggy)")
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
