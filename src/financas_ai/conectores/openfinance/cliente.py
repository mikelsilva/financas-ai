"""Cliente das APIs de recursos do Open Finance Brasil.

Depois do consentimento AUTORIZADO, estes metodos leem os dados. Seguem os
contratos oficiais:
  - Accounts API:        GET /accounts/v2/accounts
                         GET /accounts/v2/accounts/{id}/transactions
  - Credit Cards API:    GET /credit-cards-accounts/v2/accounts
                         .../{id}/transactions

As respostas do Open Finance vem paginadas (campo links.next). O cliente segue
a paginacao ate acabar.
"""
from __future__ import annotations

import requests

from .config import OpenFinanceConfig


class ClienteOpenFinance:
    def __init__(self, cfg: OpenFinanceConfig, token: str):
        self.cfg = cfg
        self.token = token

    def _get(self, url: str) -> dict:
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {self.token}"},
            cert=(self.cfg.caminho_cert, self.cfg.caminho_chave)
                 if not self.cfg.modo_mock else None,
            timeout=30,
            verify=self.cfg.verificar_tls,
        )
        resp.raise_for_status()
        return resp.json()

    def _paginar(self, url: str) -> list[dict]:
        """Segue links.next e acumula todos os itens de 'data'."""
        itens: list[dict] = []
        proxima: str | None = url
        while proxima:
            payload = self._get(proxima)
            dados = payload.get("data", [])
            itens.extend(dados if isinstance(dados, list) else [dados])
            proxima = payload.get("links", {}).get("next")
        return itens

    # ---- recursos ----

    def listar_contas(self) -> list[dict]:
        return self._paginar(f"{self.cfg.base_recursos}/accounts/v2/accounts")

    def transacoes_conta(self, account_id: str) -> list[dict]:
        return self._paginar(
            f"{self.cfg.base_recursos}/accounts/v2/accounts/{account_id}/transactions"
        )

    def listar_cartoes(self) -> list[dict]:
        return self._paginar(
            f"{self.cfg.base_recursos}/credit-cards-accounts/v2/accounts"
        )

    def transacoes_cartao(self, card_id: str) -> list[dict]:
        return self._paginar(
            f"{self.cfg.base_recursos}/credit-cards-accounts/v2/accounts/{card_id}/transactions"
        )
