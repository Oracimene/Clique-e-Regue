"""Regras do ciclo de crescimento das plantas.

Funções puras (sem Flask nem banco) para ficarem fáceis de testar.
"""

# Ações válidas do jogador e quanto progresso cada uma gera.
ACOES = {"regar": 1}


class AcaoInvalida(ValueError):
    """Ação que não pode gerar crescimento."""


def validar_estagios(estagios):
    """Garante que a lista de estágios do JSON está bem formada."""
    if not estagios:
        raise ValueError("A planta precisa ter pelo menos um estágio.")
    for estagio in estagios[:-1]:
        necessario = estagio.get("progresso_necessario")
        if not isinstance(necessario, int) or necessario <= 0:
            raise ValueError(f"Estágio '{estagio.get('id')}' precisa de progresso_necessario > 0.")
    if estagios[-1].get("progresso_necessario") is not None:
        raise ValueError("O último estágio não pode exigir progresso.")


def eh_estagio_final(estagios, estagio):
    return estagio >= len(estagios) - 1


def aplicar_acao(estagios, estagio, progresso, acao):
    """Aplica uma ação do jogador e devolve (estagio, progresso, avancou).

    - Ação desconhecida ou planta já no estágio final -> AcaoInvalida (nada muda).
    - O progresso nunca passa do limite do estágio atual.
    - Ao atingir o limite, a planta avança exatamente um estágio e o progresso zera,
      então nenhum estágio pode ser pulado.
    """
    if not isinstance(acao, str) or acao not in ACOES:
        raise AcaoInvalida("Ação inválida.")
    if eh_estagio_final(estagios, estagio):
        raise AcaoInvalida("A planta já está no estágio final.")

    necessario = estagios[estagio]["progresso_necessario"]
    progresso = min(progresso + ACOES[acao], necessario)

    if progresso >= necessario:
        return estagio + 1, 0, True
    return estagio, progresso, False
