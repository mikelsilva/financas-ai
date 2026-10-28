"""Consentimento (Consent) do Open Finance Brasil.

O consentimento e o coracao do Open Finance: antes de ler qualquer dado, o
usuario precisa AUTORIZAR, no app do proprio banco, quais permissoes e por
quanto tempo. O fluxo tem tres passos:

  1. criar o consentimento (POST /consents) -> volta consentId com status
     AWAITING_AUTHORISATION;
  2. o usuario e redirecionado ao banco e autoriza -> status vira AUTHORISED;
  3. so entao os dados podem ser lidos usando aquele consentId.

Em modo sandbox/mock o passo 2 e simulado. Em producao e um redirect real no
browser.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import requests

from .config import OpenFinanceConfig


def criar_consentimento(cfg: OpenFinanceConfig, token: str) -> dict:
    """Cria o consentimento e devolve o objeto (com consentId e status)."""
    agora = datetime.now(timezone.utc)
    corpo = {
        "data": {
            "permissions": cfg.permissions,
            # expiracao do consentimento (o Open Finance limita o prazo)
            "expirationDateTime": (agora + timedelta(days=90)).isoformat(),
            "transactionFromDateTime": (agora - timedelta(days=365)).isoformat(),
            "transactionToDateTime": agora.isoformat(),
        }
    }
    resp = requests.post(
        f"{cfg.base_recursos}/consents/v3/consents",
        json=corpo,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
        cert=(cfg.caminho_cert, cfg.caminho_chave) if not cfg.modo_mock else None,
        timeout=30,
        verify=cfg.verificar_tls,
    )
    resp.raise_for_status()
    return resp.json()["data"]


def autorizar_simulado(cfg: OpenFinanceConfig, token: str, consent_id: str) -> dict:
    """Simula o passo em que o usuario autoriza no banco.

    No sandbox existe um endpoint de automacao para isso; em producao e o
    redirect real. Aqui chamamos o atalho do nosso mock/sandbox.
    """
    resp = requests.post(
        f"{cfg.base_recursos}/consents/v3/consents/{consent_id}/authorise",
        headers={"Authorization": f"Bearer {token}"},
        cert=(cfg.caminho_cert, cfg.caminho_chave) if not cfg.modo_mock else None,
        timeout=30,
        verify=cfg.verificar_tls,
    )
    resp.raise_for_status()
    return resp.json()["data"]
