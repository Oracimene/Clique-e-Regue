import json
from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, abort, jsonify, render_template, request, url_for
from flask_login import current_user, login_required

from . import db
from .colheita import ColheitaInvalida, produzir, recompensa, segundos_para_proximo
from .crescimento import AcaoInvalida, aplicar_acao, eh_estagio_final, validar_estagios
from .models import Arvore, Jogador, Plantio

bp = Blueprint("main", __name__)

_PLANTAS_PATH = Path(__file__).parent / "data" / "plantas.json"
PLANTAS = {p["id"]: p for p in json.loads(_PLANTAS_PATH.read_text(encoding="utf-8"))}
PLANTA_INICIAL = "acai"

for _planta in PLANTAS.values():
    validar_estagios(_planta["estagios"])


def _agora():
    """Hora atual em UTC sem fuso (o SQLite não guarda fuso)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _jogador():
    jogador = db.session.get(Jogador, current_user.id)
    if jogador is None:
        jogador = Jogador(user_id=current_user.id, moedas=0, colheitas=0)
        db.session.add(jogador)
        db.session.flush()
    return jogador


def _transferir_se_pronto(plantio):
    """Quando a planta chega à produção de frutos, ela vai para a coleção
    (já com a primeira safra pronta) e o vaso recebe uma nova semente."""
    estagios = PLANTAS[plantio.planta_id]["estagios"]
    if not eh_estagio_final(estagios, plantio.estagio):
        return None
    config = PLANTAS[plantio.planta_id]["colheita"]
    arvore = Arvore(
        user_id=plantio.user_id,
        planta_id=plantio.planta_id,
        frutos=config["frutos_maximos"],
        atualizado_em=_agora(),
    )
    db.session.add(arvore)
    plantio.estagio, plantio.progresso = 0, 0
    db.session.flush()
    return arvore


def _plantio_atual():
    """Busca o plantio do jogador; na primeira vez, ele começa como semente."""
    plantio = Plantio.query.filter_by(user_id=current_user.id, planta_id=PLANTA_INICIAL).first()
    if plantio is None:
        plantio = Plantio(user_id=current_user.id, planta_id=PLANTA_INICIAL, estagio=0, progresso=0)
        db.session.add(plantio)
        db.session.commit()
    elif _transferir_se_pronto(plantio):  # plantios antigos que pararam na fase final
        db.session.commit()
    return plantio


def _estado(plantio):
    estagios = PLANTAS[plantio.planta_id]["estagios"]
    atual = estagios[plantio.estagio]
    return {
        "estagio_indice": plantio.estagio,
        "total_estagios": len(estagios),
        "estagio": {
            "id": atual["id"],
            "nome": atual["nome"],
            "descricao": atual["descricao"],
            "imagem": url_for("static", filename=atual["imagem"]),
        },
        "progresso": plantio.progresso,
        "necessario": atual["progresso_necessario"],
        "final": eh_estagio_final(estagios, plantio.estagio),
    }


def _arvore_publica(arvore, numero, agora):
    config = PLANTAS[arvore.planta_id]["colheita"]
    maximo, intervalo = config["frutos_maximos"], config["segundos_por_fruto"]
    frutos, atualizado_em = produzir(arvore.frutos, arvore.atualizado_em, agora, maximo, intervalo)
    imagem = config["imagem_com_frutos"] if frutos > 0 else config["imagem_sem_frutos"]
    return {
        "id": arvore.id,
        "nome": f"{config['nome_arvore']} #{numero}",
        "frutos": frutos,
        "frutos_maximos": maximo,
        "segundos_para_proximo": segundos_para_proximo(frutos, atualizado_em, agora, maximo, intervalo),
        "colheitas": arvore.colheitas,
        "imagem": url_for("static", filename=imagem),
    }


def _colecao():
    jogador = _jogador()
    arvores = Arvore.query.filter_by(user_id=current_user.id).order_by(Arvore.id).all()
    agora = _agora()
    return {
        "moedas": jogador.moedas,
        "colheitas": jogador.colheitas,
        "arvores": [_arvore_publica(a, i, agora) for i, a in enumerate(arvores, start=1)],
    }


@bp.route("/")
@login_required
def menu():
    return render_template("menu.html")


@bp.route("/opcoes")
@login_required
def opcoes():
    return render_template("opcoes.html")


@bp.route("/creditos")
@login_required
def creditos():
    return render_template("creditos.html")


@bp.route("/jogo")
@login_required
def jogo():
    estado = _estado(_plantio_atual())
    colecao = _colecao()
    db.session.commit()
    return render_template("jogo.html", planta=PLANTAS[PLANTA_INICIAL], estado=estado, colecao=colecao)


@bp.route("/api/plantio")
@login_required
def plantio():
    return jsonify(_estado(_plantio_atual()))


@bp.route("/api/plantio/acao", methods=["POST"])
@login_required
def plantio_acao():
    plantio = _plantio_atual()
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        dados = {}
    estagios = PLANTAS[plantio.planta_id]["estagios"]

    try:
        estagio, progresso, avancou = aplicar_acao(
            estagios, plantio.estagio, plantio.progresso, dados.get("acao")
        )
    except AcaoInvalida as erro:
        return jsonify(erro=str(erro), estado=_estado(plantio)), 400

    plantio.estagio, plantio.progresso = estagio, progresso
    nova_arvore = _transferir_se_pronto(plantio)
    db.session.commit()
    return jsonify(
        avancou=avancou,
        nova_arvore=nova_arvore is not None,
        estado=_estado(plantio),
    )


@bp.route("/api/colecao")
@login_required
def colecao():
    dados = _colecao()
    db.session.commit()
    return jsonify(dados)


@bp.route("/api/colecao/<int:arvore_id>/colher", methods=["POST"])
@login_required
def colher(arvore_id):
    arvore = Arvore.query.filter_by(id=arvore_id, user_id=current_user.id).first()
    if arvore is None:
        abort(404)

    planta = PLANTAS[arvore.planta_id]
    config = planta["colheita"]
    agora = _agora()
    frutos, _ = produzir(
        arvore.frutos, arvore.atualizado_em, agora,
        config["frutos_maximos"], config["segundos_por_fruto"],
    )

    try:
        moedas = recompensa(frutos, config["moedas_por_fruto"])
    except ColheitaInvalida as erro:
        return jsonify(erro=str(erro), colecao=_colecao()), 400

    # Só colhe se a árvore ainda estiver como foi lida: se outra requisição
    # colheu no meio do caminho, nada é alterado e a colheita repetida é recusada.
    colhida = db.session.execute(
        db.update(Arvore)
        .where(
            Arvore.id == arvore.id,
            Arvore.frutos == arvore.frutos,
            Arvore.atualizado_em == arvore.atualizado_em,
        )
        .values(frutos=0, atualizado_em=agora, colheitas=Arvore.colheitas + 1)
    ).rowcount
    if colhida != 1:
        db.session.rollback()
        return jsonify(erro="Essa colheita já foi realizada.", colecao=_colecao()), 409

    jogador = _jogador()
    db.session.execute(
        db.update(Jogador)
        .where(Jogador.user_id == jogador.user_id)
        .values(moedas=Jogador.moedas + moedas, colheitas=Jogador.colheitas + 1)
    )
    db.session.commit()
    db.session.expire_all()

    total = _jogador().colheitas
    curiosidades = config["curiosidades"]
    return jsonify(
        frutos_colhidos=frutos,
        moedas_ganhas=moedas,
        curiosidade=curiosidades[(total - 1) % len(curiosidades)],
        colecao=_colecao(),
    )


@bp.route("/api/enciclopedia/<planta_id>")
@login_required
def enciclopedia(planta_id):
    planta = PLANTAS.get(planta_id)
    if planta is None:
        abort(404)
    return jsonify(planta)
