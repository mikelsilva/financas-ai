"""Teste ponta a ponta do conector Open Finance contra o servidor mock.

Sobe o mock numa porta efemera, roda o fluxo completo e valida que os dados
chegam no schema padrao e passam pelo categorizador.
"""
import socket
import sys
import threading
import time
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ))

from sandbox_mock.servidor import servir                      # noqa: E402
from financas_ai.conectores.openfinance import ler, OpenFinanceConfig  # noqa: E402
from financas_ai.core import schema, categorizador, analise   # noqa: E402


def _porta_livre() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    porta = s.getsockname()[1]
    s.close()
    return porta


@pytest.fixture()
def servidor_mock():
    porta = _porta_livre()
    srv = servir("127.0.0.1", porta)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    time.sleep(0.3)
    yield f"http://127.0.0.1:{porta}"
    srv.shutdown()


def test_fluxo_completo(servidor_mock):
    df = ler(OpenFinanceConfig.mock(servidor_mock))
    # schema correto
    assert list(df.columns) == list(schema.COLUNAS)
    assert len(df) > 0
    # trouxe conta e cartao
    assert {"conta corrente", "cartao"} <= set(df["conta"].unique())
    assert set(df["banco"].unique()) == {"openfinance"}


def test_integra_com_categorizador_e_analise(servidor_mock):
    df = ler(OpenFinanceConfig.mock(servidor_mock))
    df = categorizador.categorizar(df)
    # entradas positivas, saidas negativas preservadas
    assert (df["valor"] != 0).all()
    serie = analise.gastos_por_categoria(df)
    assert (serie >= 0).all()


def test_sinal_credito_debito(servidor_mock):
    df = ler(OpenFinanceConfig.mock(servidor_mock))
    # 'Pix recebido' e 'Salario' sao CREDITO -> devem ser positivos
    entradas = df[df["descricao"].isin(["Pix recebido", "Salario"])]
    assert (entradas["valor"] > 0).all()
