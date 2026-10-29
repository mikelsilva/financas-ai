"""Conector Pluggy (Open Finance via Meu Pluggy — gratuito para uso pessoal).

Diferente do pynubank (engenharia reversa, instavel), a Pluggy e um agregador
REGULADO: o acesso e oficial, estavel e sem 403. No plano Meu Pluggy voce
conecta suas proprias contas de graca e consome a api.pluggy.ai com um
Client ID + Secret.

Fluxo da API:
  1. POST /auth  {clientId, clientSecret}            -> apiKey (curta duracao)
  2. GET  /accounts?itemId={item}                    -> contas do item
  3. GET  /transactions?accountId={acc}&page=N       -> transacoes (paginado)

'item' = uma conexao com um banco (voce pega o itemId no dashboard da Pluggy,
em Aplicacoes/Monitorar, depois de ativar o conector MeuPluggy).

Credenciais ficam na SUA maquina (variaveis de ambiente), nunca no codigo.
"""
from __future__ import annotations

import os

import pandas as pd
import requests

from ..core import schema

BASE = "https://api.pluggy.ai"


def _auth(client_id: str, client_secret: str) -> str:
    r = requests.post(f"{BASE}/auth",
                      json={"clientId": client_id, "clientSecret": client_secret},
                      timeout=30)
    r.raise_for_status()
    return r.json()["apiKey"]


def _get(caminho: str, api_key: str, params: dict | None = None) -> dict:
    r = requests.get(f"{BASE}{caminho}", headers={"X-API-KEY": api_key},
                     params=params or {}, timeout=30)
    r.raise_for_status()
    return r.json()


def _transacoes(api_key: str, account_id: str) -> list[dict]:
    """Segue a paginacao da Pluggy (results/totalPages) e junta tudo."""
    itens, pagina = [], 1
    while True:
        payload = _get("/transactions", api_key,
                       {"accountId": account_id, "page": pagina, "pageSize": 500})
        itens.extend(payload.get("results", []))
        if pagina >= payload.get("totalPages", 1):
            break
        pagina += 1
    return itens


def _para_linhas(trans: list[dict], conta: str) -> list[dict]:
    linhas = []
    for t in trans:
        valor = abs(float(t.get("amount", 0) or 0))
        # DEBIT = saida (negativo); CREDIT = entrada (positivo)
        if str(t.get("type", "")).upper() == "DEBIT":
            valor = -valor
        linhas.append({
            "data": pd.to_datetime(t.get("date"), errors="coerce", utc=True).tz_localize(None)
                    if t.get("date") else pd.NaT,
            "descricao": str(t.get("description") or t.get("descriptionRaw") or ""),
            "valor": valor,
            "banco": "pluggy",
            "conta": conta,
            # a Pluggy ja devolve uma categoria; guardamos para o categorizador
            # poder complementar/validar depois
            "categoria": t.get("category") if t.get("category") else pd.NA,
            "id_origem": str(t.get("id") or ""),
        })
    return linhas


def ler(item_ids: list[str] | str,
        client_id: str | None = None,
        client_secret: str | None = None) -> pd.DataFrame:
    """Le as transacoes de um ou mais itens (conexoes) e devolve o schema padrao.

    Credenciais: passe client_id/client_secret, ou defina as variaveis de
    ambiente PLUGGY_CLIENT_ID e PLUGGY_CLIENT_SECRET.
    """
    client_id = client_id or os.environ.get("PLUGGY_CLIENT_ID")
    client_secret = client_secret or os.environ.get("PLUGGY_CLIENT_SECRET")
    if not (client_id and client_secret):
        raise ValueError(
            "Defina PLUGGY_CLIENT_ID e PLUGGY_CLIENT_SECRET (ou passe como argumento)."
        )
    if isinstance(item_ids, str):
        item_ids = [item_ids]

    api_key = _auth(client_id, client_secret)

    linhas: list[dict] = []
    for item in item_ids:
        contas = _get("/accounts", api_key, {"itemId": item}).get("results", [])
        for acc in contas:
            tipo = "cartao" if str(acc.get("type", "")).upper() == "CREDIT" else "conta corrente"
            linhas += _para_linhas(_transacoes(api_key, acc["id"]), tipo)

    if not linhas:
        return schema.tabela_vazia()
    df = pd.DataFrame(linhas).dropna(subset=["data"])
    return schema.validar(df)
