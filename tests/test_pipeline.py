"""Testes do pipeline. Rode:  python -m pytest -q"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
from financas_ai import pipeline
from financas_ai.core import categorizador, analise, schema


def _consolidar_exemplos(tmp_path):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import dados.gerar_exemplos as gen
    return pipeline.consolidar({
        "nubank": gen.gerar_nubank_conta(),
        "c6": gen.gerar_c6_ofx(),
        "rico": gen.gerar_rico_csv(),
    })


def test_schema_tem_todas_as_colunas():
    df = schema.tabela_vazia()
    assert list(df.columns) == list(schema.COLUNAS)


def test_categorizador_reconhece_ifood():
    assert categorizador.categorizar_texto("Compra iFood *Restaurante") == "Delivery"
    assert categorizador.categorizar_texto("xyz desconhecido 123") == "Outros"


def test_consolida_tres_bancos(tmp_path):
    df = _consolidar_exemplos(tmp_path)
    assert set(df["banco"].unique()) == {"nubank", "c6", "rico"}
    assert len(df) > 0


def test_sem_duplicatas(tmp_path):
    df = _consolidar_exemplos(tmp_path)
    assert not df.duplicated(subset=["banco", "id_origem"]).any()


def test_analise_retorna_numeros(tmp_path):
    df = _consolidar_exemplos(tmp_path)
    serie = analise.gastos_por_categoria(df)
    assert (serie >= 0).all()
    assert isinstance(analise.total_categoria(df, "Delivery"), float)
