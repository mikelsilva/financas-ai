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


def _credito(doc_tipo=None, doc_val=None):
    t = {"id": "x", "amount": 1000, "type": "CREDIT", "date": "2026-10-05"}
    if doc_val:
        t["paymentData"] = {"payer": {"documentNumber": {"type": doc_tipo, "value": doc_val}}}
    return t


def test_entrada_cnpj_vira_salario():
    # 14 dígitos = CNPJ -> Salário
    assert pluggy._classificar_credito(_credito("CNPJ", "12345678000190"), "11122233344") == "Salário"


def test_entrada_mesmo_cpf_vira_transferencia_entre_contas():
    meu = "11122233344"
    assert pluggy._classificar_credito(_credito("CPF", meu), meu) == "Transferência entre contas"


def test_entrada_cpf_de_terceiro():
    assert pluggy._classificar_credito(_credito("CPF", "99988877766"), "11122233344") == "Pix recebido"


def test_entrada_sem_documento_vira_renda():
    assert pluggy._classificar_credito(_credito(), "11122233344") == "Renda"


def test_tipo_inferido_por_digitos():
    # sem 'type', infere pelo nº de dígitos
    assert pluggy._classificar_credito(_credito(None, "12.345.678/0001-90"), None) == "Salário"
