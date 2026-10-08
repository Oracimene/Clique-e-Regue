import pytest

from app import create_app


@pytest.fixture
def app():
    return create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})


@pytest.fixture
def cliente(app):
    cliente = app.test_client()
    cliente.post("/cadastro", data={"username": "jogador", "password": "123456", "confirm": "123456"})
    return cliente
