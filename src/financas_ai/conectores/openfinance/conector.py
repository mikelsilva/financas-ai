"""Conector Open Finance Brasil -> schema padrao do projeto.

Orquestra o fluxo completo (token -> consentimento -> autorizacao -> leitura) e
traduz o JSON do Open Finance para a mesma tabela que os conectores de arquivo
produzem. Assim o resto do sistema (categorizador, analises, bot) nao sabe nem
se importa de onde o dado veio.

Mapeamento (Accounts/Credit Cards API v2):
  transactionId      -> id_origem
  transactionName    -> descricao
  creditDebitType    -> sinal do valor (DEBITO = negativo)
  transactionAmount  -> valor
  bookingDate / transactionDateTime -> data
"""
from __future__ import annotations

import pandas as pd

from ...core import schema
from . import auth, consent
from .cliente import ClienteOpenFinance
from .config import OpenFinanceConfig


def _valor(item: dict) -> float:
    """Extrai o valor numerico, cobrindo as variacoes de nome do campo."""
    bruto = item.get("transactionAmount") or item.get("amount") or {}
    if isinstance(bruto, dict):
        valor = float(bruto.get("amount", 0) or 0)
    else:
        valor = float(bruto or 0)
    # DEBITO sai (negativo); CREDITO entra (positivo)
    if str(item.get("creditDebitType", "")).upper().startswith("DEB"):
        valor = -abs(valor)
    else:
        valor = abs(valor)
    return valor


def _data(item: dict):
    return (item.get("bookingDate")
            or item.get("transactionDateTime")
            or item.get("billPostDate"))


def _para_linhas(itens: list[dict], conta: str) -> list[dict]:
    linhas = []
    for it in itens:
        linhas.append({
            "data": pd.to_datetime(_data(it), errors="coerce"),
            "descricao": str(it.get("transactionName")
                             or it.get("type") or "transacao"),
            "valor": _valor(it),
            "banco": "openfinance",
            "conta": conta,
            "categoria": pd.NA,
            "id_origem": str(it.get("transactionId") or ""),
        })
    return linhas


def ler(cfg: OpenFinanceConfig | None = None) -> pd.DataFrame:
    """Executa o fluxo Open Finance e devolve a tabela padrao.

    Sem cfg, usa o modo mock local (precisa do servidor mock no ar).
    """
    cfg = cfg or OpenFinanceConfig.mock()

    # 1) token de acesso
    token = auth.obter_token(cfg)

    # 2) consentimento + autorizacao (simulada fora de producao)
    c = consent.criar_consentimento(cfg, token)
    consent_id = c["consentId"]
    if c.get("status") != "AUTHORISED":
        consent.autorizar_simulado(cfg, token, consent_id)

    # 3) token ligado ao consentimento e leitura dos recursos
    token = auth.obter_token(cfg, consent_id=consent_id)
    cli = ClienteOpenFinance(cfg, token)

    linhas: list[dict] = []
    for conta in cli.listar_contas():
        cid = conta["accountId"]
        linhas += _para_linhas(cli.transacoes_conta(cid), "conta corrente")
    for cartao in cli.listar_cartoes():
        kid = cartao["creditCardAccountId"]
        linhas += _para_linhas(cli.transacoes_cartao(kid), "cartao")

    if not linhas:
        return schema.tabela_vazia()

    df = pd.DataFrame(linhas).dropna(subset=["data"])
    return schema.validar(df)
