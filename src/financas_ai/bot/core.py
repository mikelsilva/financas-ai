"""Cérebro do bot financeiro (independente do canal: WhatsApp/Telegram/CLI).

Três capacidades:
  - sincronizar()     : puxa da Pluggy, salva, e detecta transações NOVAS
  - responder(p, df)  : responde uma pergunta em linguagem natural (Ollama local)
  - relatorio(df)     : monta um resumo pronto para enviar

Guarda o que já viu em dados/estado_bot.json, então 'sincronizar' só devolve o
que chegou desde a última vez — é isso que vira o "me avisa quando comprar".

Nada de API paga: Ollama roda localmente. Se o Ollama não estiver no ar, o
bot responde num modo simples por regras.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import requests

from ..conectores import pluggy
from ..core import analise, categorizador

CSV = Path("dados/meus_dados.csv")
ESTADO = Path("dados/estado_bot.json")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")


def real(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ---------- dados ----------

def carregar_csv() -> pd.DataFrame:
    if not CSV.exists():
        raise FileNotFoundError("dados/meus_dados.csv não existe. Rode 'bot.py sync' primeiro.")
    return pd.read_csv(CSV, parse_dates=["data"]).dropna(subset=["data"])


def sincronizar(item_ids: list[str] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Puxa da Pluggy, salva o CSV e devolve (df_completo, df_novas).

    df_novas = transações que ainda não tinham sido vistas (para alertar).
    """
    itens = item_ids or ([os.environ["PLUGGY_ITEM_ID"]] if os.environ.get("PLUGGY_ITEM_ID") else [])
    if not itens:
        raise ValueError("Defina PLUGGY_ITEM_ID (ou passe os item_ids).")

    df = pluggy.ler(itens)
    df = categorizador.categorizar(df, preservar=True)
    CSV.parent.mkdir(exist_ok=True)
    df.to_csv(CSV, index=False)

    vistos = _carregar_estado()
    ids_atuais = set(df["id_origem"].dropna().astype(str))
    novos_ids = ids_atuais - vistos
    novas = df[df["id_origem"].astype(str).isin(novos_ids)].sort_values("data")

    _salvar_estado(vistos | ids_atuais)
    return df, novas


def _carregar_estado() -> set[str]:
    if ESTADO.exists():
        try:
            return set(json.loads(ESTADO.read_text()).get("vistos", []))
        except Exception:
            return set()
    return set()


def _salvar_estado(ids: set[str]) -> None:
    ESTADO.parent.mkdir(exist_ok=True)
    ESTADO.write_text(json.dumps({"vistos": sorted(ids)}))


# ---------- alertas ----------

def formatar_alerta(novas: pd.DataFrame) -> str:
    """Mensagem de alerta das compras novas. Vazio => sem novidades."""
    saidas = novas[novas["valor"] < 0]
    entradas = novas[novas["valor"] > 0]
    if len(saidas) == 0 and len(entradas) == 0:
        return ""

    linhas = ["🔔 *Novidades na sua conta*", ""]
    for _, t in saidas.iterrows():
        linhas.append(f"🔴 {t['descricao'][:40]} — {real(abs(t['valor']))}  _{t['categoria']}_")
    for _, t in entradas.iterrows():
        linhas.append(f"🟢 {t['descricao'][:40]} — {real(t['valor'])}  _{t['categoria']}_")
    total_gasto = float(saidas["valor"].sum()) * -1
    if total_gasto > 0:
        linhas += ["", f"Total das novas saídas: *{real(total_gasto)}*"]
    return "\n".join(linhas)


# ---------- relatório ----------

def relatorio(df: pd.DataFrame, mes: str | None = None) -> str:
    cats = analise.gastos_por_categoria(df, mes)
    em = analise.evolucao_mensal(df)
    ult = em.iloc[-1] if len(em) else None

    linhas = ["📊 *Resumo financeiro*", ""]
    if ult is not None:
        linhas.append(f"Mês atual: entradas {real(ult.entradas)} · saídas {real(ult.saidas)} · saldo {real(ult.saldo)}")
    linhas += ["", "*Gastos por categoria:*"]
    for c, v in cats.head(6).items():
        linhas.append(f"• {c}: {real(v)}")
    return "\n".join(linhas)


# ---------- perguntas (Ollama) ----------

def _contexto(df: pd.DataFrame) -> str:
    """Resumo compacto dos dados para dar de contexto ao modelo."""
    cats = analise.gastos_por_categoria(df)
    em = analise.evolucao_mensal(df)
    partes = [
        f"Total de transações: {len(df)}.",
        "Gastos por categoria (período): " + "; ".join(f"{c}={real(v)}" for c, v in cats.items()) + ".",
        "Fluxo mensal (entradas/saidas/saldo): " + "; ".join(
            f"{i}: {real(r.entradas)}/{real(r.saidas)}/{real(r.saldo)}" for i, r in em.iterrows()) + ".",
    ]
    recentes = df.sort_values("data").tail(12)
    partes.append("Transações recentes: " + "; ".join(
        f"{r['data'].date()} {r['descricao'][:30]} {real(r['valor'])} ({r['categoria']})"
        for _, r in recentes.iterrows()) + ".")
    return "\n".join(partes)


def responder(pergunta: str, df: pd.DataFrame) -> str:
    """Responde via Ollama local; cai para um modo simples se ele não responder."""
    contexto = _contexto(df)
    sistema = (
        "Você é um assistente financeiro pessoal em português do Brasil. "
        "Responda à pergunta do usuário usando SOMENTE os dados fornecidos. "
        "Seja direto e claro, use valores em reais (R$). Se os dados não "
        "permitirem responder, diga isso com honestidade. Não invente números."
    )
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "stream": False,
                "messages": [
                    {"role": "system", "content": sistema},
                    {"role": "user", "content": f"Dados:\n{contexto}\n\nPergunta: {pergunta}"},
                ],
            },
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["message"]["content"].strip()
    except Exception:
        return _responder_regras(pergunta, df)


def _responder_regras(pergunta: str, df: pd.DataFrame) -> str:
    """Fallback sem IA: cobre algumas perguntas comuns."""
    p = pergunta.lower()
    cats = analise.gastos_por_categoria(df)
    if "saldo" in p:
        em = analise.evolucao_mensal(df)
        if len(em):
            return f"Seu saldo no mês atual é {real(em.iloc[-1].saldo)}."
    for c in cats.index:
        if c.lower() in p:
            return f"Você gastou {real(cats[c])} com {c} no período."
    if "maior" in p or "maiores" in p:
        m = analise.maiores_gastos(df, n=3)
        itens = "; ".join(f"{r['descricao'][:30]} {real(r['valor'])}" for _, r in m.iterrows())
        return f"Seus maiores gastos: {itens}."
    return ("(Ollama offline) Posso responder sobre saldo, gastos por categoria "
            "e maiores gastos. Ligue o Ollama para respostas completas.")
