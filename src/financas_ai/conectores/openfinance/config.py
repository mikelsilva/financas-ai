"""Configuracao do conector Open Finance Brasil.

Separa o que muda entre "mock" (roda aqui, sem certificado) e "sandbox"
(ambiente oficial de teste do Open Finance, com dados sinteticos e
certificados que VOCE gera no diretorio de sandbox).

Nada de segredo fica no codigo: caminhos de certificado e client_id vem de
variaveis de ambiente quando em modo sandbox.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class OpenFinanceConfig:
    # URLs base. No mock, apontam para o servidor local.
    base_auth: str                      # emissor OAuth2 (authorization server)
    base_recursos: str                  # API de recursos (accounts, etc.)

    client_id: str = "client-mock"
    # escopos e permissoes que vamos pedir no consentimento
    scopes: str = "openid accounts credit-cards-accounts resources consents"
    permissions: list[str] = field(default_factory=lambda: [
        "ACCOUNTS_READ",
        "ACCOUNTS_BALANCES_READ",
        "ACCOUNTS_TRANSACTIONS_READ",
        "CREDIT_CARDS_ACCOUNTS_READ",
        "CREDIT_CARDS_ACCOUNTS_TRANSACTIONS_READ",
        "RESOURCES_READ",
    ])

    # Seguranca FAPI. No mock ficam vazios e o fluxo usa atalhos.
    caminho_cert: str | None = None     # certificado de transporte (mTLS), .pem
    caminho_chave: str | None = None    # chave privada de assinatura, .pem
    verificar_tls: bool = True

    @property
    def modo_mock(self) -> bool:
        """Sem chave de assinatura configurada => modo mock."""
        return not self.caminho_chave

    # ---- construtores de conveniencia ----

    @classmethod
    def mock(cls, host: str = "http://127.0.0.1:8777") -> "OpenFinanceConfig":
        return cls(base_auth=host, base_recursos=host, verificar_tls=False)

    @classmethod
    def sandbox_do_ambiente(cls) -> "OpenFinanceConfig":
        """Le as configuracoes reais do sandbox a partir de variaveis de ambiente.

        Defina antes de usar:
            OFB_BASE_AUTH, OFB_BASE_RECURSOS, OFB_CLIENT_ID,
            OFB_CERT, OFB_CHAVE
        """
        return cls(
            base_auth=os.environ["OFB_BASE_AUTH"],
            base_recursos=os.environ["OFB_BASE_RECURSOS"],
            client_id=os.environ.get("OFB_CLIENT_ID", "client-sandbox"),
            caminho_cert=os.environ.get("OFB_CERT"),
            caminho_chave=os.environ.get("OFB_CHAVE"),
        )
