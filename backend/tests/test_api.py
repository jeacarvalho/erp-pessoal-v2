from __future__ import annotations

import os
from typing import Set

from fastapi.testclient import TestClient

from backend.app.main import SQLITE_DB_PATH, app


def _configure_test_database() -> None:
    """Configura o banco SQLite para testes de API.

    Usa um arquivo dedicado para evitar interferência com o banco real.
    A existência do arquivo é removida antes da criação para forçar o seed
    inicial definido no evento de startup da aplicação.
    """

    # Garante que usamos um arquivo de banco dedicado aos testes de API.
    os.environ.setdefault("SQLITE_DB_PATH", "test_api.db")

    db_path = os.getenv("SQLITE_DB_PATH", "test_api.db")
    if os.path.exists(db_path):
        os.remove(db_path)


_configure_test_database()

client = TestClient(app)


def test_categories_endpoint_contains_expected_categories() -> None:
    """Garante que o endpoint /categories retorna categorias seeds esperadas."""

    response = client.get("/categories")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)

    category_names: Set[str] = {item["name"] for item in data}

    # Categorias específicas que devem existir após o seed:
    # - "Portugal 202606" (filha de "Viagem")
    # - "Saúde" (categoria raiz)
    assert "Portugal 202606" in category_names
    assert "Saúde" in category_names

