"""Pipeline: le os arquivos dos bancos, consolida, deduplica e categoriza.

Ponto de entrada principal da biblioteca. Uso tipico:

    from financas_ai import pipeline
    df = pipeline.consolidar({
        "nubank": "dados/meu_extrato_nubank.csv",
        "c6": "dados/meu_extrato_c6.ofx",
        "rico": "dados/minha_movimentacao_rico.xlsx",
    })
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd

from .conectores import nubank, c6, rico
from .core import schema, categorizador

_CONECTORES = {
    "nubank": nubank.ler,
    "c6": c6.ler,
    "rico": rico.ler,
}


def consolidar(arquivos: dict[str, str | Path]) -> pd.DataFrame:
    """Recebe {banco: caminho} e devolve a tabela unica, categorizada."""
    partes = []
    for banco, caminho in arquivos.items():
        if banco not in _CONECTORES:
            raise ValueError(f"Banco sem conector: {banco}. Disponiveis: {list(_CONECTORES)}")
        partes.append(_CONECTORES[banco](caminho))

    if not partes:
        return schema.tabela_vazia()

    df = pd.concat(partes, ignore_index=True)
    # dedup: mesma transacao nao pode entrar duas vezes (ex.: reexport)
    df = df.drop_duplicates(subset=["banco", "id_origem"]).reset_index(drop=True)
    df = categorizador.categorizar(df)
    df = df.sort_values("data").reset_index(drop=True)
    return df
