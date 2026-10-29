"""Categorizador por regras.

Nao usa IA nem API paga: casa o texto da transacao contra uma lista de padroes
(regex). E deterministico, rapido e transparente -- da pra explicar numa
entrevista exatamente por que cada gasto caiu em cada categoria.

As regras sao avaliadas em ordem: a primeira que casar vence. Por isso regras
mais especificas devem vir antes das mais genericas.
"""
from __future__ import annotations

import re
import pandas as pd

# (categoria, padrao_regex). Tudo e comparado em minusculas.
# Edite aqui pra ensinar o sistema a reconhecer novos estabelecimentos.
REGRAS: list[tuple[str, str]] = [
    ("Renda",            r"sal[aá]rio|pagamento recebido|transfer[eê]ncia recebida|pix recebido|rendimento|dividendo|jcp|cashback|estorno|reembolso"),
    ("Investimentos",    r"\brdb\b|aplica[cç][aã]o|resgate|tesouro|\bcdb\b|\blci\b|\blca\b|renda fixa|caixinha|nu reserva|compra de ativo|corretagem|\bb3\b"),
    ("Dívidas",          r"renegocia|pend[eê]ncia|acordo de|parcelamento de fatura|pagamento de fatura|cobran[cç]a"),
    ("Delivery",         r"ifood|rappi|z[eé] delivery|uber eats|aiqfome|delivery"),
    ("Transporte",       r"uber|99app|99pop|99 \*|cabify|posto|shell|ipiranga|petrobras|combust[ií]vel|estacionamento|metr[oô]|bilhete [uú]nico|passagem|latam|gol |azul "),
    ("Mercado",          r"supermerc|mercado\b|carrefour|p[aã]o de a[cç][uú]car|assa[ií]|atacad|atacarejo|hortifrut|sacol[aã]o|a[cç]ougue|mercearia|com[eé]rcio de alim|comercio ataca|\bataca\b"),
    ("Saude",            r"farm[aá]cia|drogaria|drogasil|raia|pacheco|pague menos|hospital|cl[ií]nica|laborat[oó]rio|unimed|odonto|academia|smart ?fit|procfit|bio ?ritmo|gympass|totalpass|wellhub"),
    ("Educacao",         r"faculdade|fiap|curso|udemy|alura|coursera|escola|livraria|mensalidade"),
    ("Moradia",          r"aluguel|condom[ií]nio|energia|enel|cpfl|light\b|sabesp|comg[aá]s|internet|vivo\b|claro\b|\btim\b|net\b|telefon"),
    ("Assinaturas",      r"netflix|spotify|amazon prime|prime video|disney|\bhbo\b|\bmax\b|youtube|apple\.com|icloud|playstation|xbox|canva|chatgpt|openai"),
    ("Compras",          r"amazon|mercado ?livre|mercado ?pago|shopee|aliexpress|magazine|magalu|americanas|renner|riachuelo|zara|c&a|nike|adidas|centauro|netshoes|ecommer|shein|loja\b|shopping"),
    ("Restaurante",      r"restaurante|\bbar\b|lanchonete|padaria|pizzaria|hamburgueria|cafeteria|caf[eé]|starbucks|mcdonald|burger|pizza|subway|outback"),
    ("Tarifas",          r"tarifa|anuidade|\biof\b|multa|encargo|\btaxa\b|juros"),
    ("Transferências",   r"pix enviado|transfer[eê]ncia enviada|\bted\b|\bdoc\b"),
    ("Saques",           r"saque"),
]

_REGRAS_COMPILADAS = [(cat, re.compile(pad, re.IGNORECASE)) for cat, pad in REGRAS]
CATEGORIA_PADRAO = "Outros"


def categorizar_texto(descricao: str) -> str:
    """Categoria de uma unica descricao."""
    if not isinstance(descricao, str):
        return CATEGORIA_PADRAO
    for categoria, padrao in _REGRAS_COMPILADAS:
        if padrao.search(descricao):
            return categoria
    return CATEGORIA_PADRAO


def categorizar(df: pd.DataFrame) -> pd.DataFrame:
    """Preenche a coluna 'categoria' do DataFrame inteiro.

    Regra de negocio: entradas (valor > 0) que nao casaram com nada viram
    'Renda' por padrao, porque quase todo credito nao-classificado e receita.
    """
    df = df.copy()
    df["categoria"] = df["descricao"].map(categorizar_texto).astype("string")
    entrada_sem_cat = (df["valor"] > 0) & (df["categoria"] == CATEGORIA_PADRAO)
    df.loc[entrada_sem_cat, "categoria"] = "Renda"
    return df


def cobertura(df: pd.DataFrame) -> float:
    """% de transacoes que cairam em alguma categoria que nao 'Outros'.

    Metrica util pra saber se vale a pena adicionar mais regras.
    """
    if len(df) == 0:
        return 0.0
    classificadas = (df["categoria"] != CATEGORIA_PADRAO).sum()
    return round(100 * classificadas / len(df), 1)
