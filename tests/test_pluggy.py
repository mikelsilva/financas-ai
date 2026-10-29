"""Testa o mapeamento Pluggy -> schema (sem rede, sem credenciais).

Usa um payload sintetico no formato da api.pluggy.ai (campos id, description,
amount, date, type, category).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
from financas_ai.conectores import pluggy
from financas_ai.core import schema

TRANS = [
    {"id": "a1", "description": "Compra iFood", "amount": 48.90,
     "date": "2026-10-07T00:00:00.000Z", "type": "DEBIT", "category": "Food"},
    {"id": "a2", "description": "Salário", "amount": 5500.00,
     "date": "2026-10-05T00:00:00.000Z", "type": "CREDIT", "category": "Income"},
    {"id": "a3", "description": "Pix enviado", "amount": 200.0,
     "date": "2026-10-09T00:00:00.000Z", "type": "DEBIT"},
]


def test_sinal_debit_credit():
    linhas = pluggy._para_linhas(TRANS, "conta corrente")
    por_id = {l["id_origem"]: l for l in linhas}
    assert por_id["a1"]["valor"] == -48.90   # DEBIT
    assert por_id["a2"]["valor"] == 5500.00  # CREDIT
    assert por_id["a3"]["valor"] == -200.0   # DEBIT


def test_schema_e_banco():
    df = schema.validar(pd.DataFrame(pluggy._para_linhas(TRANS, "cartao")))
    assert list(df.columns) == list(schema.COLUNAS)
    assert (df["banco"] == "pluggy").all()
    assert (df["conta"] == "cartao").all()


def test_data_convertida():
    linhas = pluggy._para_linhas(TRANS, "conta corrente")
    assert all(isinstance(l["data"], pd.Timestamp) for l in linhas)
