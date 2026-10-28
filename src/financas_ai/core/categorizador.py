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
    ("Renda",            r"salario|pagamento recebido|pix recebido|transferencia recebida|rendimento|dividendo|jcp"),
    ("Delivery",         r"ifood|rappi|ze delivery|zedelivery|uber eats"),
    ("Transporte",       r"uber|99app|99 \*|cabify|posto|shell|ipiranga|combustivel|estacionamento|metro|bilhete unico"),
    ("Mercado",          r"supermerc|mercado|carrefour|pao de acucar|assai|atacadao|hortifruti|sacolao"),
    ("Restaurante",      r"restaurante|bar |lanchonete|padaria|cafe|starbucks|mcdonald|burger|pizza"),
    ("Assinaturas",      r"netflix|spotify|amazon prime|disney|hbo|max|youtube premium|apple.com/bill|google.*youtube|icloud"),
    ("Saude",            r"farmacia|drogaria|drogasil|raia|pacheco|hospital|clinica|laboratorio|unimed|odonto"),
    ("Educacao",         r"faculdade|curso|udemy|alura|coursera|escola|livraria"),
    ("Moradia",          r"aluguel|condominio|energia|enel|cpfl|light|sabesp|comgas|internet|vivo|claro|tim|net "),
    ("Compras",          r"amazon|mercado livre|mercadolivre|shopee|aliexpress|magazine|americanas|renner|zara|shopping"),
    ("Investimentos",    r"aplicacao|resgate|tesouro|cdb|aplic\.|compra de ativo|corretagem|b3"),
    ("Tarifas",          r"tarifa|anuidade|juros|iof|multa|encargo"),
    ("Transferencias",   r"pix enviado|ted |doc |transferencia enviada"),
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
