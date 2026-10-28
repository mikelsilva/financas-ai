"""Leitor de OFX tolerante.

OFX e o formato padrao de extrato bancario (C6, Itau, BB e quase todo banco
exportam nele). E um "quase-XML" cheio de tags sem fechamento, entao um parser
XML normal quebra. Este le na marra com regex, o que funciona bem para os
extratos reais dos bancos brasileiros.

Sem dependencia externa de propósito -- OFX varia entre bancos e um parser
proprio e mais facil de ajustar do que brigar com uma lib generica.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


def _texto_ofx(caminho: str | Path) -> str:
    # OFX brasileiro costuma vir em latin-1; cai pra utf-8 se precisar.
    bruto = Path(caminho).read_bytes()
    for enc in ("latin-1", "utf-8"):
        try:
            return bruto.decode(enc)
        except UnicodeDecodeError:
            continue
    return bruto.decode("latin-1", errors="replace")


def _tag(bloco: str, nome: str) -> str | None:
    m = re.search(rf"<{nome}>([^<\r\n]*)", bloco, re.IGNORECASE)
    return m.group(1).strip() if m else None


def _data(valor: str | None) -> datetime | None:
    if not valor:
        return None
    # formato YYYYMMDD... as vezes com hora e fuso colados.
    m = re.match(r"(\d{4})(\d{2})(\d{2})", valor)
    if not m:
        return None
    ano, mes, dia = map(int, m.groups())
    return datetime(ano, mes, dia)


def ler_transacoes(caminho: str | Path) -> list[dict]:
    """Devolve uma lista de dicts com data, descricao, valor, id_origem."""
    texto = _texto_ofx(caminho)
    transacoes = []
    for bloco in re.findall(r"<STMTTRN>(.*?)</STMTTRN>", texto, re.IGNORECASE | re.DOTALL):
        data = _data(_tag(bloco, "DTPOSTED"))
        valor = _tag(bloco, "TRNAMT")
        memo = _tag(bloco, "MEMO") or _tag(bloco, "NAME") or ""
        fitid = _tag(bloco, "FITID")
        if data is None or valor is None:
            continue
        transacoes.append({
            "data": data,
            "descricao": memo,
            "valor": float(valor.replace(",", ".")),
            "id_origem": fitid or f"{data:%Y%m%d}-{memo[:20]}-{valor}",
        })
    return transacoes
