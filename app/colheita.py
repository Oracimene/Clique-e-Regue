"""Regras de produção e colheita das árvores da coleção.

Funções puras (sem Flask nem banco) para ficarem fáceis de testar.
"""

from datetime import timedelta


class ColheitaInvalida(ValueError):
    """Colheita que não pode ser realizada."""


def produzir(frutos, atualizado_em, agora, maximo, segundos_por_fruto):
    """Calcula quantos frutos a árvore tem agora.

    A árvore ganha 1 fruto a cada `segundos_por_fruto`, até `maximo`.
    Devolve (frutos, atualizado_em), em que `atualizado_em` marca o início
    da contagem do próximo fruto. O resultado nunca é negativo.
    """
    frutos = max(0, min(frutos, maximo))
    if frutos >= maximo:
        return maximo, agora

    decorrido = (agora - atualizado_em).total_seconds()
    if decorrido <= 0:
        return frutos, atualizado_em

    novos = int(decorrido // segundos_por_fruto)
    if frutos + novos >= maximo:
        return maximo, agora
    return frutos + novos, atualizado_em + timedelta(seconds=novos * segundos_por_fruto)


def segundos_para_proximo(frutos, atualizado_em, agora, maximo, segundos_por_fruto):
    """Segundos até o próximo fruto, ou None se a árvore está cheia."""
    if frutos >= maximo:
        return None
    decorrido = (agora - atualizado_em).total_seconds()
    return max(0, int(segundos_por_fruto - decorrido + 0.999))


def recompensa(frutos, moedas_por_fruto):
    """Moedas recebidas ao colher `frutos`. Sem frutos, não há colheita."""
    if frutos <= 0:
        raise ColheitaInvalida("Ainda não há frutos para colher.")
    return frutos * moedas_por_fruto
