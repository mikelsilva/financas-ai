"""Autenticacao OAuth2 / FAPI-BR do Open Finance Brasil.

O Open Finance nao usa OAuth2 "comum". Ele segue o perfil FAPI-BR, que exige:
  - client assertion via private_key_jwt (o cliente assina um JWT com sua chave
    privada em vez de mandar um client_secret);
  - PAR (Pushed Authorization Request): a requisicao de autorizacao e enviada
    antes, pelo backend, e o browser so recebe um request_uri;
  - mTLS: o canal usa certificado de transporte.

Aqui implementamos a ESTRUTURA correta desse fluxo. Em modo mock, os atalhos
(sem crypto/mTLS) deixam rodar localmente; em modo sandbox, a mesma funcao
assina o JWT de verdade e usa os certificados.
"""
from __future__ import annotations

import time
import uuid

import requests

from .config import OpenFinanceConfig


def _client_assertion(cfg: OpenFinanceConfig) -> str:
    """Monta o JWT assinado (private_key_jwt) que autentica o cliente.

    So e chamado em modo sandbox (quando ha chave privada).
    """
    import jwt  # PyJWT

    agora = int(time.time())
    payload = {
        "iss": cfg.client_id,
        "sub": cfg.client_id,
        "aud": f"{cfg.base_auth}/token",
        "jti": str(uuid.uuid4()),
        "iat": agora,
        "exp": agora + 300,
    }
    chave = open(cfg.caminho_chave).read()
    return jwt.encode(payload, chave, algorithm="PS256")


def _mtls(cfg: OpenFinanceConfig):
    """Tupla (cert, chave) para o parametro cert= do requests, ou None no mock."""
    if cfg.caminho_cert and cfg.caminho_chave:
        return (cfg.caminho_cert, cfg.caminho_chave)
    return None


def obter_token(cfg: OpenFinanceConfig, consent_id: str | None = None) -> str:
    """Executa o client credentials / token exchange e devolve o access_token.

    No fluxo real de dados do usuario, o token vem apos o consentimento ser
    autorizado no banco; aqui encapsulamos as duas pontas (mock e sandbox).
    """
    if cfg.modo_mock:
        # mock: o servidor local emite um token de teste sem crypto
        resp = requests.post(
            f"{cfg.base_auth}/token",
            data={"grant_type": "client_credentials", "scope": cfg.scopes,
                  "consent_id": consent_id or ""},
            timeout=30,
            verify=cfg.verificar_tls,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    # sandbox / producao
    dados = {
        "grant_type": "client_credentials",
        "scope": cfg.scopes,
        "client_assertion_type":
            "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
        "client_assertion": _client_assertion(cfg),
    }
    if consent_id:
        dados["consent_id"] = consent_id
    resp = requests.post(
        f"{cfg.base_auth}/token",
        data=dados,
        cert=_mtls(cfg),
        timeout=30,
        verify=cfg.verificar_tls,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]
