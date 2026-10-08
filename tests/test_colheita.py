from datetime import datetime, timedelta

import pytest

from app.colheita import ColheitaInvalida, produzir, recompensa, segundos_para_proximo

T0 = datetime(2026, 1, 1, 12, 0, 0)


def test_produz_um_fruto_por_intervalo():
    assert produzir(0, T0, T0 + timedelta(seconds=65), 5, 30) == (2, T0 + timedelta(seconds=60))


def test_producao_para_no_maximo():
    agora = T0 + timedelta(hours=10)
    assert produzir(0, T0, agora, 5, 30) == (5, agora)


def test_frutos_nunca_ficam_negativos():
    assert produzir(-3, T0, T0, 5, 30)[0] == 0


def test_relogio_voltando_nao_tira_frutos():
    assert produzir(2, T0, T0 - timedelta(minutes=5), 5, 30) == (2, T0)


def test_segundos_para_proximo():
    assert segundos_para_proximo(0, T0, T0 + timedelta(seconds=10), 5, 30) == 20
    assert segundos_para_proximo(5, T0, T0, 5, 30) is None


def test_recompensa():
    assert recompensa(5, 2) == 10


@pytest.mark.parametrize("frutos", [0, -1])
def test_sem_frutos_nao_ha_colheita(frutos):
    with pytest.raises(ColheitaInvalida):
        recompensa(frutos, 2)
