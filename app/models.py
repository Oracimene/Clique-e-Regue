from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from . import db, login_manager


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Plantio(db.Model):
    """Planta que um jogador está cultivando e em que ponto do crescimento ela está."""

    __table_args__ = (db.UniqueConstraint("user_id", "planta_id"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    planta_id = db.Column(db.String(40), nullable=False)
    estagio = db.Column(db.Integer, nullable=False, default=0)  # 0 = semente
    progresso = db.Column(db.Integer, nullable=False, default=0)


class Jogador(db.Model):
    """Recursos do jogador: moedas e total de colheitas realizadas."""

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)
    moedas = db.Column(db.Integer, nullable=False, default=0)
    colheitas = db.Column(db.Integer, nullable=False, default=0)


class Arvore(db.Model):
    """Árvore adulta na coleção do jogador, produzindo frutos com o tempo."""

    __table_args__ = (db.CheckConstraint("frutos >= 0", name="frutos_nao_negativos"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    planta_id = db.Column(db.String(40), nullable=False)
    frutos = db.Column(db.Integer, nullable=False, default=0)
    # Início da contagem do próximo fruto (UTC, sem fuso).
    atualizado_em = db.Column(db.DateTime, nullable=False)
    colheitas = db.Column(db.Integer, nullable=False, default=0)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
