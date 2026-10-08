import pytest

from app.crescimento import AcaoInvalida, aplicar_acao, validar_estagios
from app.main import PLANTAS

ESTAGIOS = [
    {"id": "a", "progresso_necessario": 3},
    {"id": "b", "progresso_necessario": 2},
    {"id": "c", "progresso_necessario": None},
]


def test_acao_valida_aumenta_progresso():
    assert aplicar_acao(ESTAGIOS, 0, 0, "regar") == (0, 1, False)


def test_atingir_limite_muda_de_estagio():
    assert aplicar_acao(ESTAGIOS, 0, 2, "regar") == (1, 0, True)


def test_progresso_nao_ultrapassa_o_limite_nem_pula_estagio():
    # Mesmo com progresso acima do limite (dado corrompido), avança só um estágio.
    assert aplicar_acao(ESTAGIOS, 0, 99, "regar") == (1, 0, True)


@pytest.mark.parametrize("acao", [None, "", "pular", "REGAR", 5, ["regar"]])
def test_acao_invalida_nao_gera_crescimento(acao):
    with pytest.raises(AcaoInvalida):
        aplicar_acao(ESTAGIOS, 0, 1, acao)


def test_estagio_final_nao_cresce_mais():
    with pytest.raises(AcaoInvalida):
        aplicar_acao(ESTAGIOS, 2, 0, "regar")


def test_ciclo_completo_passa_por_todos_os_estagios_em_ordem():
    estagio, progresso, visitados = 0, 0, [0]
    while estagio < len(ESTAGIOS) - 1:
        estagio, progresso, avancou = aplicar_acao(ESTAGIOS, estagio, progresso, "regar")
        if avancou:
            visitados.append(estagio)
    assert visitados == [0, 1, 2]


def test_estagios_do_acai():
    estagios = PLANTAS["acai"]["estagios"]
    validar_estagios(estagios)
    assert [e["id"] for e in estagios] == [
        "semente", "germinacao", "muda", "jovem", "adulto", "frutos",
    ]
    # Cada estágio tem uma representação visual diferente.
    assert len({e["imagem"] for e in estagios}) == len(estagios)


@pytest.mark.parametrize("estagios", [
    [],
    [{"id": "a", "progresso_necessario": 0}, {"id": "b", "progresso_necessario": None}],
    [{"id": "a", "progresso_necessario": 1}, {"id": "b", "progresso_necessario": 5}],
])
def test_validar_estagios_rejeita_dados_ruins(estagios):
    with pytest.raises(ValueError):
        validar_estagios(estagios)
