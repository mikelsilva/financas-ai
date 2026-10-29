"""CLI do bot financeiro — o 'cérebro' que o WhatsApp/Telegram vai usar.

Comandos:
  python bot.py sync                      # puxa da Pluggy e mostra as compras NOVAS
  python bot.py perguntar "quanto gastei com delivery?"
  python bot.py relatorio                 # resumo pronto para enviar

'sync' é o que detecta novidades (base do "me avisa quando comprar").
As respostas usam Ollama local (modo simples se ele estiver desligado).
Rode na SUA máquina — credenciais ficam só aí.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from financas_ai.bot import core


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]

    if cmd == "sync":
        try:
            df, novas = core.sincronizar()
        except Exception as e:
            print(f"❌ {e}")
            sys.exit(1)
        print(f"Sincronizado: {len(df)} transações no total, {len(novas)} nova(s).\n")
        msg = core.formatar_alerta(novas)
        print(msg if msg else "Nenhuma novidade desde a última sincronização.")

    elif cmd == "perguntar":
        if len(sys.argv) < 3:
            print('Uso: python bot.py perguntar "sua pergunta"'); sys.exit(1)
        df = core.carregar_csv()
        print(core.responder(" ".join(sys.argv[2:]), df))

    elif cmd == "relatorio":
        df = core.carregar_csv()
        print(core.relatorio(df))

    else:
        print(f"Comando desconhecido: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
