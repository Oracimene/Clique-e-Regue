def regar(cliente, acao="regar"):
    return cliente.post("/api/plantio/acao", json={"acao": acao})


def test_planta_comeca_como_semente(cliente):
    estado = cliente.get("/api/plantio").get_json()
    assert estado["estagio"]["id"] == "semente"
    assert estado["progresso"] == 0
    assert estado["estagio_indice"] == 0


def test_tela_do_jogo_mostra_estagio_atual(cliente):
    html = cliente.get("/jogo").get_data(as_text=True)
    assert "Semente" in html
    assert "img/acai/1-semente.svg" in html


def test_regar_aumenta_progresso_e_persiste(cliente):
    resp = regar(cliente)
    assert resp.status_code == 200
    assert resp.get_json()["estado"]["progresso"] == 1
    assert cliente.get("/api/plantio").get_json()["progresso"] == 1


def test_acao_invalida_retorna_400_sem_crescer(cliente):
    for corpo in [{"acao": "pular_estagio"}, {}, ["regar"], {"acao": None}]:
        resp = cliente.post("/api/plantio/acao", json=corpo)
        assert resp.status_code == 400
    resp = cliente.post("/api/plantio/acao", data="regar")  # sem JSON
    assert resp.status_code == 400
    assert cliente.get("/api/plantio").get_json()["progresso"] == 0


def test_ciclo_completo_leva_arvore_para_colecao(cliente):
    vistos = ["semente"]
    for _ in range(1000):
        resp = regar(cliente).get_json()
        novo = resp["estado"]
        assert novo["progresso"] <= novo["necessario"]
        if resp["nova_arvore"]:
            break
        if resp["avancou"]:
            vistos.append(novo["estagio"]["id"])
    else:
        raise AssertionError("A planta nunca chegou à produção de frutos")

    assert vistos == ["semente", "germinacao", "muda", "jovem", "adulto"]
    # O vaso recebe uma nova semente e a árvore vai para a coleção.
    assert novo["estagio"]["id"] == "semente"
    assert len(cliente.get("/api/colecao").get_json()["arvores"]) == 1


def test_api_exige_login(app):
    cliente = app.test_client()
    assert cliente.post("/api/plantio/acao", json={"acao": "regar"}).status_code == 302
