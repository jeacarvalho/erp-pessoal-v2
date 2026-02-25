"""
Teste E2E para importação de XML da SEFAZ RJ.
"""

import os
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app, get_db
from app.models import Base
from app.seed import get_session_factory


def test_xml_rj_import():
    """Testa a importação de XML da SEFAZ RJ usando arquivo real."""

    # Remove banco de teste anterior se existir
    test_db = "test_xml_rj.db"
    if os.path.exists(test_db):
        os.remove(test_db)

    # Configura banco de dados em arquivo para teste
    engine = create_engine(
        f"sqlite:///{test_db}", connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Cria as tabelas
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)

    # Usa o XML real da SEFAZ RJ
    xml_path = (
        Path(__file__).parent.parent.parent
        / "data"
        / "NFe33260208628825000329654080004340459599397569.xml"
    )

    with open(xml_path, "rb") as f:
        response = client.post(
            "/import/xml-rj", files={"file": (xml_path.name, f, "application/xml")}
        )

    assert response.status_code == 200, response.text
    response_data = response.json()

    assert "note_id" in response_data
    assert response_data["seller_name"] == "SUPERMERCADO PADRAO DO FONSECA LTDA"
    assert response_data["items_count"] == 32  # XML RJ tem 32 itens
    assert response_data["total_amount"] == 297.47

    # Consulta a nota importada
    note_id = response_data["note_id"]
    detail_response = client.get(f"/fiscal-notes/{note_id}")
    assert detail_response.status_code == 200

    note_details = detail_response.json()
    assert note_details["seller_name"] == "SUPERMERCADO PADRAO DO FONSECA LTDA"
    assert note_details["total_amount"] == 297.47
    assert len(note_details["items"]) == 32

    app.dependency_overrides.clear()
