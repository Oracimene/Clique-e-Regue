from datetime import timedelta

import pytest

import app.main as main
from app import db
from app.models import Arvore, Plantio


def levar_ate_a_colecao(app, cliente):
    """Deixa o plantio a um clique da produção de frutos e rega uma vez."""
    cliente.get("/api/plantio")
    with app.app_context():
        plantio = Plantio.query.first()
        plantio.estagio, plantio.progresso = 4, 59
        db.session.commit()
    resp = cliente.post("/api/plantio/acao", json={"acao": "regar"}).get_json()
    assert resp["nova_arvore"] is True
    return cliente.get("/api/colecao").get_json()["arvores"][0]


@pytest.fixture
def relogio(monkeypatch):
    """Relógio controlável pelos testes."""
    atual = {"agora": main._agora()}
    monkeypatch.setattr(main, "_agora", lambda: atual["agora"])

    def avancar(segundos):
        atual["agora"] += timedelta(seconds=segundos)

    return avancar


def colher(cliente, arvore_id):
    return cliente.post(f"/api/colecao/{arvore_id}/colher")


def test_colecao_comeca_vazia_e_sem_moedas(cliente):
    colecao = cliente.get("/api/colecao").get_json()
    assert colecao == {"moedas": 0, "colheitas": 0, "arvores": []}


def test_arvore_chega_na_colecao_com_frutos(app, cliente, relogio):
    arvore = levar_ate_a_colecao(app, cliente)
    assert arvore["nome"] == "Açaizeiro #1"
    assert arvore["frutos"] == arvore["frutos_maximos"] == 5
    assert "6-frutos.svg" in arvore["imagem"]


def test_colheita_da_recompensa_registra_e_mostra_curiosidade(app, cliente, relogio):
    arvore = levar_ate_a_colecao(app, cliente)
    resp = colher(cliente, arvore["id"])
    assert resp.status_code == 200
    dados = resp.get_json()
    assert dados["frutos_colhidos"] == 5
    assert dados["moedas_ganhas"] == 10
    assert dados["curiosidade"]
    assert dados["colecao"]["moedas"] == 10
    assert dados["colecao"]["colheitas"] == 1
    depois = dados["colecao"]["arvores"][0]
    assert depois["frutos"] == 0
    assert depois["colheitas"] == 1
    assert "5-adulto.svg" in depois["imagem"]


def test_nao_permite_colher_a_mesma_colheita_duas_vezes(app, cliente, relogio):
    arvore = levar_ate_a_colecao(app, cliente)
    assert colher(cliente, arvore["id"]).status_code == 200
    resp = colher(cliente, arvore["id"])
    assert resp.status_code == 400
    assert resp.get_json()["colecao"]["moedas"] == 10
    assert resp.get_json()["colecao"]["colheitas"] == 1


def test_colheita_concorrente_e_recusada(app, cliente, relogio, monkeypatch):
    """Se outra requisição colher entre a leitura e a gravação, nada muda."""
    arvore = levar_ate_a_colecao(app, cliente)
    original = main.recompensa

    def colher_no_meio(frutos, moedas_por_fruto):
        with app.app_context():
            outra = db.session.get(Arvore, arvore["id"])
            outra.frutos = 0
            db.session.commit()
        return original(frutos, moedas_por_fruto)

    monkeypatch.setattr(main, "recompensa", colher_no_meio)
    resp = colher(cliente, arvore["id"])
    assert resp.status_code == 409
    assert resp.get_json()["colecao"]["moedas"] == 0


def test_frutos_renascem_com_o_tempo(app, cliente, relogio):
    arvore = levar_ate_a_colecao(app, cliente)
    colher(cliente, arvore["id"])

    relogio(29)
    assert colher(cliente, arvore["id"]).status_code == 400  # ainda não nasceu
    relogio(1)
    resp = colher(cliente, arvore["id"]).get_json()
    assert resp["frutos_colhidos"] == 1
    assert resp["colecao"]["moedas"] == 12
    assert resp["colecao"]["colheitas"] == 2


def test_nao_colhe_arvore_que_nao_existe_ou_de_outro_jogador(app, cliente, relogio):
    arvore = levar_ate_a_colecao(app, cliente)
    assert colher(cliente, 9999).status_code == 404

    outro = app.test_client()
    outro.post("/cadastro", data={"username": "outro", "password": "123456", "confirm": "123456"})
    assert colher(outro, arvore["id"]).status_code == 404


def test_banco_recusa_frutos_negativos(app, cliente, relogio):
    arvore = levar_ate_a_colecao(app, cliente)
    with app.app_context(), pytest.raises(Exception):
        db.session.get(Arvore, arvore["id"]).frutos = -1
        db.session.commit()


def test_plantio_antigo_parado_na_fase_final_vai_para_a_colecao(app, cliente):
    cliente.get("/api/plantio")
    with app.app_context():
        Plantio.query.first().estagio = 5
        db.session.commit()
    assert cliente.get("/api/plantio").get_json()["estagio"]["id"] == "semente"
    assert len(cliente.get("/api/colecao").get_json()["arvores"]) == 1
