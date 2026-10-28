"""Schema padrao de uma transacao.

Todo conector, nao importa o banco de origem, precisa devolver um DataFrame
com exatamente estas colunas. E isso que permite consolidar C6, Nubank e Rico
na mesma tabela e analisar tudo junto.
"""
from __future__ import annotations

import pandas as pd

# Colunas canonicas e seus tipos. A ordem aqui e a ordem oficial da tabela.
COLUNAS: dict[str, str] = {
    "data": "datetime64[ns]",   # dia da transacao
    "descricao": "string",       # texto cru que o banco mostra
    "valor": "float64",          # negativo = saida, positivo = entrada
    "banco": "string",           # c6 | nubank | rico
    "conta": "string",           # ex.: "cartao", "conta corrente", "corretora"
    "categoria": "string",       # preenchido depois pelo categorizador
    "id_origem": "string",       # id/hash da transacao no arquivo original
}


def tabela_vazia() -> pd.DataFrame:
    """DataFrame vazio ja com as colunas e tipos certos."""
    df = pd.DataFrame({col: pd.Series(dtype=tipo) for col, tipo in COLUNAS.items()})
    return df


def validar(df: pd.DataFrame) -> pd.DataFrame:
    """Garante que o DataFrame bate com o schema. Levanta erro se faltar coluna.

    Devolve o DataFrame reordenado e com os tipos ajustados, pronto pra uso.
    """
    faltando = set(COLUNAS) - set(df.columns)
    if faltando:
        raise ValueError(f"Faltam colunas no conector: {sorted(faltando)}")

    df = df[list(COLUNAS)].copy()
    df["data"] = pd.to_datetime(df["data"])
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    for col in ("descricao", "banco", "conta", "categoria", "id_origem"):
        df[col] = df[col].astype("string")
    return df
