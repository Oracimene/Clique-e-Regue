from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from . import db
from .models import User

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.menu"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash("Usuário ou senha incorretos.", "erro")
            return render_template("auth.html", aba="login")
        login_user(user)
        return redirect(url_for("main.menu"))

    return render_template("auth.html", aba="login")


@bp.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if current_user.is_authenticated:
        return redirect(url_for("main.menu"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        erro = None
        if not 3 <= len(username) <= 20:
            erro = "O usuário deve ter entre 3 e 20 caracteres."
        elif len(password) < 6:
            erro = "A senha deve ter pelo menos 6 caracteres."
        elif password != confirm:
            erro = "As senhas não conferem."
        elif User.query.filter_by(username=username).first():
            erro = "Esse nome de usuário já está em uso."

        if erro:
            flash(erro, "erro")
            return render_template("auth.html", aba="cadastro")

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash(f"Bem-vindo(a), {username}!", "sucesso")
        return redirect(url_for("main.menu"))

    return render_template("auth.html", aba="cadastro")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
