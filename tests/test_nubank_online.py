"""Testa o mapeamento feed->schema do conector Nubank online.

Nao faz rede nem precisa de credenciais: usa um feed sintetico no mesmo formato
do GraphQL do Nubank (campos id, title, detail, amount, postDate, __typename).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from financas_ai.conectores import nubank_online as nb
from financas_ai.core import schema

FEED_CONTA = [
    {"id": "1", "title": "Transferência recebida", "detail": "Salario",
     "amount": 5500.0, "postDate": "2026-10-05", "__typename": "TransferInEvent"},
    {"id": "2", "title": "Transferência enviada", "detail": "Aluguel",
     "amount": 1800.0, "postDate": "2026-10-06", "__typename": "TransferOutEvent"},
    {"id": "3", "title": "Pagamento de boleto", "detail": "Energia",
     "amount": 220.5, "postDate": "2026-10-10", "__typename": "BarcodePaymentEvent"},
]

FEED_CARTAO = [
    {"id": "10", "title": "iFood", "detail": "", "amount": 48.9,
     "postDate": "2026-10-07", "__typename": "TransactionEvent"},
]


def test_sinal_entrada_e_saida():
    linhas = nb.feed_para_linhas(FEED_CONTA, "conta corrente")
    por_id = {l["id_origem"]: l for l in linhas}
    assert por_id["1"]["valor"] > 0      # recebida = entrada
    assert por_id["2"]["valor"] < 0      # enviada = saida
    assert por_id["3"]["valor"] < 0      # pagamento = saida


def test_cartao_e_sempre_saida():
    linhas = nb.feed_para_linhas(FEED_CARTAO, "cartao")
    assert linhas[0]["valor"] < 0
    assert linhas[0]["conta"] == "cartao"


def test_sai_no_schema_padrao():
    import pandas as pd
    linhas = nb.feed_para_linhas(FEED_CONTA, "conta corrente")
    df = schema.validar(pd.DataFrame(linhas))
    assert list(df.columns) == list(schema.COLUNAS)
    assert (df["banco"] == "nubank").all()
