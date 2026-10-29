"""Testa o cérebro do bot (partes sem rede: alertas, relatório, fallback)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
from financas_ai.bot import core
from financas_ai.core import schema


def _df():
    linhas = [
        {"data": "2026-10-05", "descricao": "Salário - ACME LTDA", "valor": 5000.0,
         "banco": "pluggy", "conta": "conta corrente", "categoria": "Salário", "id_origem": "a"},
        {"data": "2026-10-07", "descricao": "iFood", "valor": -50.0,
         "banco": "pluggy", "conta": "cartao", "categoria": "Delivery", "id_origem": "b"},
        {"data": "2026-10-09", "descricao": "Mercado X", "valor": -200.0,
         "banco": "pluggy", "conta": "conta corrente", "categoria": "Mercado", "id_origem": "c"},
    ]
    return schema.validar(pd.DataFrame(linhas))


def test_alerta_lista_novas():
    df = _df()
    msg = core.formatar_alerta(df[df["id_origem"].isin(["b", "c"])])
    assert "iFood" in msg and "Mercado X" in msg
    assert "Novidades" in msg


def test_alerta_vazio_quando_sem_novas():
    df = _df()
    assert core.formatar_alerta(df.iloc[0:0]) == ""


def test_relatorio_tem_categorias():
    r = core.relatorio(_df())
    assert "Resumo" in r
    assert "Mercado" in r or "Delivery" in r


def test_fallback_responde_categoria():
    # sem Ollama, o modo por regras deve achar a categoria citada
    resp = core._responder_regras("quanto gastei com delivery?", _df())
    assert "Delivery" in resp and "R$" in resp


def test_fallback_saldo():
    resp = core._responder_regras("qual meu saldo?", _df())
    assert "saldo" in resp.lower()
