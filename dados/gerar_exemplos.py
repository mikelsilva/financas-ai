"""Gera arquivos de exemplo SINTETICOS nos formatos reais de cada banco.

Nada aqui e dado real -- sao transacoes inventadas so para demonstrar o
pipeline. Rode:  python dados/gerar_exemplos.py
"""
from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)
AQUI = Path(__file__).parent / "exemplos"
AQUI.mkdir(exist_ok=True)

ESTABELECIMENTOS = [
    ("iFood *Restaurante", 25, 90, "Delivery"),
    ("Uber *Trip", 8, 45, "Transporte"),
    ("Supermercado Pao de Acucar", 40, 350, "Mercado"),
    ("Netflix.com", 39, 55, "Assinaturas"),
    ("Spotify", 21, 35, "Assinaturas"),
    ("Drogasil", 15, 120, "Saude"),
    ("Amazon BR", 30, 400, "Compras"),
    ("Posto Shell", 80, 250, "Transporte"),
    ("Starbucks", 18, 40, "Restaurante"),
    ("Udemy", 25, 60, "Educacao"),
]


def _meses():
    hoje = date.today().replace(day=1)
    return [(hoje - timedelta(days=30 * i)).replace(day=1) for i in range(5, -1, -1)]


def gerar_nubank_conta() -> Path:
    """CSV no formato do extrato NuConta: Data, Valor, Identificador, Descricao."""
    linhas = []
    for mes in _meses():
        # salario
        linhas.append([mes.replace(day=5).strftime("%d/%m/%Y"), "5500.00",
                       f"sal-{mes:%Y%m}", "Transferencia recebida - Salario"])
        for _ in range(random.randint(8, 14)):
            nome, lo, hi, _cat = random.choice(ESTABELECIMENTOS)
            dia = mes.replace(day=random.randint(6, 28))
            val = -round(random.uniform(lo, hi), 2)
            linhas.append([dia.strftime("%d/%m/%Y"), f"{val:.2f}",
                           f"nu-{dia:%Y%m%d}-{random.randint(1000,9999)}",
                           f"Compra no debito - {nome}"])
    p = AQUI / "nubank_conta.csv"
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Data", "Valor", "Identificador", "Descricao"])
        w.writerows(linhas)
    return p


def gerar_c6_ofx() -> Path:
    """OFX simplificado do cartao C6."""
    trns = []
    for mes in _meses():
        for _ in range(random.randint(6, 12)):
            nome, lo, hi, _cat = random.choice(ESTABELECIMENTOS)
            dia = mes.replace(day=random.randint(2, 27))
            val = -round(random.uniform(lo, hi), 2)
            trns.append((dia, nome, val))
    corpo = "".join(
        f"<STMTTRN><TRNTYPE>DEBIT<DTPOSTED>{d:%Y%m%d}000000<TRNAMT>{v:.2f}"
        f"<FITID>c6{d:%Y%m%d}{i}<MEMO>{n}</STMTTRN>\n"
        for i, (d, n, v) in enumerate(trns)
    )
    ofx = (
        "OFXHEADER:100\nDATA:OFXSGML\n\n"
        "<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS><BANKTRANLIST>\n"
        f"{corpo}"
        "</BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>\n"
    )
    p = AQUI / "c6_cartao.ofx"
    p.write_text(ofx, encoding="latin-1")
    return p


def gerar_rico_csv() -> Path:
    """Movimentacao da corretora Rico."""
    linhas = []
    for mes in _meses():
        linhas.append([mes.replace(day=10).strftime("%d/%m/%Y"), "Aplicacao Tesouro Selic", "-1000,00"])
        if random.random() < 0.5:
            linhas.append([mes.replace(day=20).strftime("%d/%m/%Y"), "Dividendo ITSA4", f"{random.uniform(5,80):.2f}".replace(".", ",")])
    p = AQUI / "rico_movimentacao.csv"
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Data", "Movimentacao", "Valor"])
        w.writerows(linhas)
    return p


if __name__ == "__main__":
    for fn in (gerar_nubank_conta, gerar_c6_ofx, gerar_rico_csv):
        print("gerado:", fn())
