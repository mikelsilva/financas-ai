"""Conector Nubank.

O Nubank exporta dois tipos de arquivo:
  - Extrato da conta (NuConta): CSV com colunas Data, Valor, Identificador, Descricao
  - Fatura do cartao: CSV com colunas date, title, amount

Este conector detecta qual dos dois e e normaliza os dois para o schema padrao.
Como obter: app Nubank -> Conta/Cartao -> ... -> Exportar (ou pelo site).
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd

from ..core import schema


def _normaliza_colunas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    return df


def ler(caminho: str | Path) -> pd.DataFrame:
    bruto = _normaliza_colunas(pd.read_csv(caminho))
    out = schema.tabela_vazia()

    if {"date", "title", "amount"} <= set(bruto.columns):
        # fatura do cartao: amount positivo = gasto, entao invertemos o sinal
        out = pd.DataFrame({
            "data": pd.to_datetime(bruto["date"]),
            "descricao": bruto["title"].astype("string"),
            "valor": -pd.to_numeric(bruto["amount"], errors="coerce"),
            "conta": "cartao",
        })
    elif {"data", "valor", "descricao"} <= set(bruto.columns):
        # extrato da conta: valor ja vem com sinal (negativo = saida)
        out = pd.DataFrame({
            "data": pd.to_datetime(bruto["data"], dayfirst=True),
            "descricao": bruto["descricao"].astype("string"),
            "valor": pd.to_numeric(bruto["valor"], errors="coerce"),
            "conta": "conta corrente",
        })
        if "identificador" in bruto.columns:
            out["id_origem"] = bruto["identificador"].astype("string")
    else:
        raise ValueError(
            f"CSV do Nubank nao reconhecido. Colunas: {list(bruto.columns)}"
        )

    out["banco"] = "nubank"
    if "id_origem" not in out or out["id_origem"].isna().all():
        out["id_origem"] = (
            out["data"].dt.strftime("%Y%m%d") + "-" + out["descricao"].str.slice(0, 20)
        )
    out["categoria"] = pd.NA
    return schema.validar(out)
