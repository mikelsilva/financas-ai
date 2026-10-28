"""Analises sobre a tabela consolidada.

Cada funcao aqui responde um tipo de pergunta que o usuario faria em linguagem
natural ("quanto gastei com delivery em maio?"). A camada conversacional
(opcional) so precisa escolher qual destas chamar.
"""
from __future__ import annotations

import pandas as pd


def _apenas_saidas(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["valor"] < 0].copy()


def gastos_por_categoria(df: pd.DataFrame, mes: str | None = None) -> pd.Series:
    """Total gasto (valor absoluto) por categoria. mes no formato 'YYYY-MM'."""
    saidas = _apenas_saidas(df)
    if mes:
        saidas = saidas[saidas["data"].dt.strftime("%Y-%m") == mes]
    return saidas.groupby("categoria")["valor"].sum().abs().sort_values(ascending=False)


def total_categoria(df: pd.DataFrame, categoria: str, mes: str | None = None) -> float:
    """Quanto saiu numa categoria especifica."""
    serie = gastos_por_categoria(df, mes)
    return float(serie.get(categoria, 0.0))


def evolucao_mensal(df: pd.DataFrame) -> pd.DataFrame:
    """Entradas, saidas e saldo por mes."""
    g = df.copy()
    g["mes"] = g["data"].dt.strftime("%Y-%m")
    entradas = g[g["valor"] > 0].groupby("mes")["valor"].sum()
    saidas = g[g["valor"] < 0].groupby("mes")["valor"].sum().abs()
    out = pd.DataFrame({"entradas": entradas, "saidas": saidas}).fillna(0.0)
    out["saldo"] = out["entradas"] - out["saidas"]
    return out.sort_index()


def maiores_gastos(df: pd.DataFrame, n: int = 10, mes: str | None = None) -> pd.DataFrame:
    saidas = _apenas_saidas(df)
    if mes:
        saidas = saidas[saidas["data"].dt.strftime("%Y-%m") == mes]
    saidas = saidas.assign(valor_abs=saidas["valor"].abs())
    return saidas.nlargest(n, "valor_abs")[["data", "descricao", "valor", "categoria", "banco"]]


def possiveis_recorrencias(df: pd.DataFrame) -> pd.DataFrame:
    """Heuristica de assinaturas/cobrancas recorrentes: mesma descricao
    normalizada aparecendo em 3+ meses distintos com valor parecido.
    E mais ou menos o que o Pierre chama de 'cobrancas futuras'.
    """
    saidas = _apenas_saidas(df).copy()
    saidas["chave"] = saidas["descricao"].str.lower().str.replace(r"\d", "", regex=True).str.strip()
    saidas["mes"] = saidas["data"].dt.strftime("%Y-%m")
    agg = saidas.groupby("chave").agg(
        ocorrencias=("mes", "nunique"),
        valor_medio=("valor", "mean"),
        exemplo=("descricao", "first"),
    )
    recorrentes = agg[agg["ocorrencias"] >= 3].copy()
    recorrentes["valor_medio"] = recorrentes["valor_medio"].round(2)
    return recorrentes.sort_values("ocorrencias", ascending=False)
