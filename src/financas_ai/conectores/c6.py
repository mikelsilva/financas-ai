"""Conector C6 Bank.

O C6 exporta extrato em OFX (conta e fatura do cartao). OFX ja traz o sinal
certo: negativo = saida, positivo = entrada. Reaproveitamos o leitor de OFX
compartilhado.
Como obter: app C6 -> Extrato -> Exportar -> OFX.
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd

from ..core import schema
from . import ofx


def ler(caminho: str | Path, conta: str = "conta corrente") -> pd.DataFrame:
    transacoes = ofx.ler_transacoes(caminho)
    if not transacoes:
        raise ValueError(f"Nenhuma transacao encontrada no OFX: {caminho}")

    out = pd.DataFrame(transacoes)
    out["banco"] = "c6"
    out["conta"] = conta
    out["categoria"] = pd.NA
    return schema.validar(out)
