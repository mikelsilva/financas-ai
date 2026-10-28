"""Servidor mock do Open Finance Brasil.

Responde aos mesmos endpoints e no mesmo FORMATO da spec oficial (token,
consents, accounts, credit-cards-accounts, transactions com paginacao), mas com
dados sinteticos e sem exigir certificado. Serve para desenvolver e testar o
conector localmente.

Nao e o sandbox oficial -- e uma imitacao fiel do contrato para rodar offline.
Roda com a biblioteca padrao, sem Flask:

    python sandbox_mock/servidor.py            # sobe em 127.0.0.1:8777
"""
from __future__ import annotations

import json
import random
import re
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

random.seed(7)

ESTAB = [
    ("iFood *Restaurante", "DEBITO"), ("Uber *Trip", "DEBITO"),
    ("Supermercado Pao de Acucar", "DEBITO"), ("Netflix.com", "DEBITO"),
    ("Spotify", "DEBITO"), ("Drogasil", "DEBITO"), ("Amazon BR", "DEBITO"),
    ("Posto Shell", "DEBITO"), ("Pix recebido", "CREDITO"),
    ("Salario", "CREDITO"),
]

_ACCOUNT_ID = "acc-0001"
_CARD_ID = "card-0001"


def _transacoes(qtd: int, campo_data: str) -> list[dict]:
    hoje = datetime.now(timezone.utc)
    out = []
    for i in range(qtd):
        nome, cd = random.choice(ESTAB)
        valor = round(random.uniform(15, 400), 2)
        if nome == "Salario":
            valor = 5500.00
        d = (hoje - timedelta(days=random.randint(0, 150)))
        out.append({
            "transactionId": f"tx-{i:04d}",
            "transactionName": nome,
            "type": "PIX" if "Pix" in nome else "CARTAO",
            "creditDebitType": cd,
            "transactionAmount": {"amount": f"{valor:.2f}", "currency": "BRL"},
            campo_data: d.strftime("%Y-%m-%d"),
        })
    return out


def _paginado(itens: list[dict], self_url: str, pagina: int, por_pagina: int = 25) -> dict:
    # self_url ja chega absoluto (http://host/...), como no Open Finance real
    ini = (pagina - 1) * por_pagina
    fatia = itens[ini:ini + por_pagina]
    tem_proxima = ini + por_pagina < len(itens)
    links = {"self": self_url}
    if tem_proxima:
        base = re.sub(r"[?&]page=\d+", "", self_url)
        sep = "&" if "?" in base else "?"
        links["next"] = f"{base}{sep}page={pagina+1}"
    return {"data": fatia, "links": links, "meta": {"totalRecords": len(itens)}}


# cache de transacoes para paginar de forma estavel
_TX_CONTA = _transacoes(60, "bookingDate")
_TX_CARTAO = _transacoes(40, "billPostDate")


class Handler(BaseHTTPRequestHandler):
    def _responder(self, obj: dict, status: int = 200):
        corpo = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _pagina(self) -> int:
        m = re.search(r"[?&]page=(\d+)", self.path)
        return int(m.group(1)) if m else 1

    def _url_abs(self) -> str:
        host = self.headers.get("Host", "127.0.0.1:8777")
        return f"http://{host}{self.path}"

    def log_message(self, *a):  # silencia o log padrao
        pass

    def do_POST(self):
        if self.path.endswith("/token"):
            self._responder({"access_token": "mock-token", "token_type": "Bearer",
                             "expires_in": 300})
        elif re.search(r"/consents/v3/consents/[^/]+/authorise$", self.path):
            self._responder({"data": {"status": "AUTHORISED"}})
        elif self.path.endswith("/consents/v3/consents"):
            self._responder({"data": {
                "consentId": "urn:mock:consent-123",
                "status": "AWAITING_AUTHORISATION",
            }}, status=201)
        else:
            self._responder({"erro": "rota nao encontrada"}, status=404)

    def do_GET(self):
        p = self.path.split("?")[0]
        if p.endswith("/accounts/v2/accounts"):
            self._responder({"data": [{"accountId": _ACCOUNT_ID, "type": "CONTA_DEPOSITO_A_VISTA"}],
                             "links": {"self": self._url_abs()}})
        elif re.search(rf"/accounts/v2/accounts/{_ACCOUNT_ID}/transactions$", p):
            self._responder(_paginado(_TX_CONTA, self._url_abs(), self._pagina()))
        elif p.endswith("/credit-cards-accounts/v2/accounts"):
            self._responder({"data": [{"creditCardAccountId": _CARD_ID, "name": "Cartao Mock"}],
                             "links": {"self": self._url_abs()}})
        elif re.search(rf"/credit-cards-accounts/v2/accounts/{_CARD_ID}/transactions$", p):
            self._responder(_paginado(_TX_CARTAO, self._url_abs(), self._pagina()))
        else:
            self._responder({"erro": "rota nao encontrada"}, status=404)


def servir(host: str = "127.0.0.1", porta: int = 8777) -> HTTPServer:
    srv = HTTPServer((host, porta), Handler)
    return srv


if __name__ == "__main__":
    s = servir()
    print("mock Open Finance em http://127.0.0.1:8777  (ctrl+c para parar)")
    s.serve_forever()
