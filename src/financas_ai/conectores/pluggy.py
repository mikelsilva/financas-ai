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
from datetime import date, timedelta

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


def _proximo_cursor(payload: dict) -> str | None:
    """Acha o cursor da proxima pagina cobrindo os formatos que a Pluggy usa."""
    return (payload.get("nextCursor")
            or (payload.get("page") or {}).get("nextCursor")
            or (payload.get("cursors") or {}).get("next"))


def _tentar(api_key: str, params: dict) -> requests.Response:
    return requests.get(f"{BASE}/v2/transactions",
                        headers={"X-API-KEY": api_key}, params=params, timeout=30)


def _transacoes(api_key: str, account_id: str, dias: int = 720) -> list[dict]:
    """Lê as transações via endpoint v2 (paginação por cursor).

    Desde jun/2026 a Pluggy descontinuou o /transactions por página para contas
    novas (410 Gone); o caminho atual é /v2/transactions com cursor. Como o
    contrato exato de parâmetros varia, tentamos combinações da mais completa
    à mais simples e usamos a primeira que a API aceitar (200).
    """
    de = (date.today() - timedelta(days=dias)).isoformat()
    ate = date.today().isoformat()
    tentativas = [
        {"accountId": account_id, "from": de, "to": ate, "pageSize": 100},
        {"accountId": account_id, "from": de, "to": ate},
        {"accountId": account_id, "pageSize": 100},
        {"accountId": account_id},
    ]

    base = None
    primeira = None
    ultima: requests.Response | None = None
    for p in tentativas:
        r = _tentar(api_key, p)
        ultima = r
        if r.status_code == 200:
            base, primeira = p, r.json()
            break
    if base is None:
        corpo = ""
        try:
            corpo = (ultima.text or "")[:400]
        except Exception:
            pass
        raise RuntimeError(
            f"/v2/transactions respondeu {ultima.status_code}. Resposta da Pluggy: {corpo}"
        )

    itens: list[dict] = list(primeira.get("results", []))
    cursor = _proximo_cursor(primeira)
    for _ in range(200):  # teto de segurança
        if not cursor:
            break
        payload = _get("/v2/transactions", api_key, {**base, "cursor": cursor})
        itens.extend(payload.get("results", []))
        cursor = _proximo_cursor(payload)
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
    contas_lidas = 0
    erros: list[str] = []
    for item in item_ids:
        contas = _get("/accounts", api_key, {"itemId": item}).get("results", [])
        for acc in contas:
            tipo = "cartao" if str(acc.get("type", "")).upper() == "CREDIT" else "conta corrente"
            try:
                linhas += _para_linhas(_transacoes(api_key, acc["id"]), tipo)
                contas_lidas += 1
            except Exception as e:
                # nao derruba tudo por causa de uma conta problematica
                erros.append(f"{acc.get('name') or acc['id']}: {e}")

    # so levanta erro se NENHUMA conta pode ser lida
    if contas_lidas == 0 and erros:
        raise RuntimeError("Falha ao ler transações:\n  " + "\n  ".join(erros))

    if not linhas:
        return schema.tabela_vazia()
    df = pd.DataFrame(linhas).dropna(subset=["data"])
    return schema.validar(df)
