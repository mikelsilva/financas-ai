"""Conector Rico (corretora).

A Rico e investimentos, nao conta corrente. O que interessa aqui e a
movimentacao: aportes, resgates, proventos (dividendos/JCP) e corretagem.

A Rico permite exportar a movimentacao em Excel/CSV. Os nomes de coluna mudam
de tempos em tempos, entao o conector tenta mapear por aproximacao.
Como obter: site Rico -> Extratos/Movimentacao -> exportar Excel.
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd

from ..core import schema

# possiveis nomes -> nome canonico interno
_MAPA = {
    "data": ["data", "data do negocio", "data liquidacao", "data movimentacao"],
    "descricao": ["descricao", "movimentacao", "evento", "tipo", "produto", "ativo"],
    "valor": ["valor", "valor liquido", "valor (r$)", "financeiro", "valor financeiro"],
}


def _acha(colunas: list[str], candidatos: list[str]) -> str | None:
    cols = {c.strip().lower(): c for c in colunas}
    for cand in candidatos:
        if cand in cols:
            return cols[cand]
    return None


def ler(caminho: str | Path) -> pd.DataFrame:
    p = Path(caminho)
    if p.suffix.lower() in (".xlsx", ".xls"):
        bruto = pd.read_excel(p)
    else:
        bruto = pd.read_csv(p, sep=None, engine="python")

    col_data = _acha(list(bruto.columns), _MAPA["data"])
    col_desc = _acha(list(bruto.columns), _MAPA["descricao"])
    col_valor = _acha(list(bruto.columns), _MAPA["valor"])
    if not (col_data and col_valor):
        raise ValueError(
            f"Planilha da Rico nao reconhecida. Colunas: {list(bruto.columns)}"
        )

    out = pd.DataFrame({
        "data": pd.to_datetime(bruto[col_data], dayfirst=True, errors="coerce"),
        "descricao": (bruto[col_desc] if col_desc else "movimentacao").astype("string"),
        "valor": pd.to_numeric(
            bruto[col_valor].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
            errors="coerce",
        ),
    })
    out = out.dropna(subset=["data", "valor"])
    out["banco"] = "rico"
    out["conta"] = "corretora"
    out["id_origem"] = out["data"].dt.strftime("%Y%m%d") + "-" + out["descricao"].str.slice(0, 20)
    out["categoria"] = pd.NA
    return schema.validar(out)
