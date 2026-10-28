"""Conector Nubank "ao vivo" (API nao-oficial).

Portado da logica que o projeto ja tinha em TypeScript (lib/nubank-unofficial),
agora em Python sobre a biblioteca `pynubank` -- que faz exatamente o mesmo
fluxo de engenharia reversa:

  1. discovery dos endpoints dinamicos do Nubank;
  2. autenticacao por CPF + senha gerando um certificado .p12 no 1o uso
     (login por QR code no app, ou por codigo enviado no e-mail);
  3. reuso do certificado nas proximas vezes (sem novo login);
  4. leitura do feed da conta e da fatura do cartao via GraphQL.

IMPORTANTE -- SEGURANCA:
  Este conector usa suas credenciais do Nubank. Rode SOMENTE na sua maquina.
  O certificado .p12 fica no seu computador; nunca suba ele pro Git
  (o .gitignore do projeto ja ignora *.p12 e a pasta de credenciais).

pynubank e dependencia OPCIONAL: so e importada quando voce de fato usa este
conector. O mapeamento feed->schema (a parte testavel) nao depende dela.
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd

from ..core import schema

# Palavras no __typename do evento que indicam ENTRADA (credito).
# O feed do Nubank traz 'amount' sempre positivo; o sinal vem do tipo do evento.
_TIPOS_ENTRADA = ("in", "received", "deposit", "reward", "credit", "transferin")
_TIPOS_SAIDA = ("out", "payment", "purchase", "debit", "billpayment", "transferout", "barcode")


def _sinal_do_evento(evento: dict, conta: str) -> float:
    valor = abs(float(evento.get("amount", 0) or 0))
    tipo = str(evento.get("__typename", "")).lower()
    titulo = str(evento.get("title", "")).lower()

    if any(t in tipo for t in _TIPOS_ENTRADA) or "recebid" in titulo:
        return valor
    if any(t in tipo for t in _TIPOS_SAIDA) or "enviad" in titulo or "pagamento" in titulo:
        return -valor
    # fatura do cartao: evento sem tipo claro e quase sempre compra (saida)
    return -valor if conta == "cartao" else valor


def feed_para_linhas(feed: list[dict], conta: str) -> list[dict]:
    """Converte o feed GraphQL do Nubank em linhas do schema padrao.

    Esta funcao e pura (nao faz rede), entao da pra testar com dados sinteticos.
    Campos do feed: id, title, detail, amount, postDate, __typename.
    """
    linhas = []
    for ev in feed:
        descricao = ev.get("title") or ""
        if ev.get("detail"):
            descricao = f"{descricao} - {ev['detail']}"
        linhas.append({
            "data": pd.to_datetime(ev.get("postDate") or ev.get("time"), errors="coerce"),
            "descricao": descricao.strip(" -"),
            "valor": _sinal_do_evento(ev, conta),
            "banco": "nubank",
            "conta": conta,
            "categoria": pd.NA,
            "id_origem": str(ev.get("id") or ""),
        })
    return linhas


def ler(cpf: str, senha: str, caminho_cert: str = "nubank_cert.p12") -> pd.DataFrame:
    """Autentica no Nubank e devolve conta + cartao no schema padrao.

    Primeiro uso (sem certificado): faz login por QR code -- abra o app do
    Nubank, va em Perfil > Acesso pelo site/app autorizado e escaneie o QR
    que aparece no terminal. O certificado e salvo em `caminho_cert` e
    reutilizado depois.
    """
    try:
        from pynubank import Nubank  # dependencia opcional
    except ImportError as e:
        raise ImportError(
            "pynubank nao instalado. Rode: pip install pynubank  "
            "(use este conector apenas na sua maquina, com suas credenciais)."
        ) from e

    nu = Nubank()
    if Path(caminho_cert).exists():
        nu.authenticate_with_cert(cpf, senha, caminho_cert)
    else:
        # login por QR code; gera e salva o certificado
        uuid, qr = nu.get_qr_code()
        qr.print_ascii(invert=True)
        input("Escaneie o QR no app do Nubank e aperte Enter...")
        nu.authenticate_with_qr_code(cpf, senha, uuid)
        nu.save_certs(caminho_cert)  # reuso futuro

    linhas = feed_para_linhas(nu.get_account_feed(), "conta corrente")
    linhas += feed_para_linhas(nu.get_card_feed(), "cartao")

    if not linhas:
        return schema.tabela_vazia()
    df = pd.DataFrame(linhas).dropna(subset=["data"])
    return schema.validar(df)
