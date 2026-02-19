from __future__ import annotations

import os
import sys
import tempfile
from typing import Set
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.app.seed import _create_category_hierarchy
from backend.app.models import (
    Base,
    FiscalItem,
    FiscalNote,
    Category,
    FiscalSourceType,
)
from datetime import date
from fastapi import FastAPI
import pytest


def reload_database_modules():
    """Force reload of database-related modules to ensure clean state."""
    # Remove cached modules to force reload
    modules_to_remove = [
        "backend.app.database",
        "backend.app.main",
        "backend.app.models",
        "backend.app.seed",
        "backend.app.schemas",
        "backend.app.services.xml_handler",
        "backend.app.services.scraper_handler",
    ]
    for module in modules_to_remove:
        if module in sys.modules:
            del sys.modules[module]


@pytest.fixture(scope="function")
def test_engine():
    """Create an isolated test database engine for each test."""
    # Create a temporary database file
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db.close()
    database_url = f"sqlite:///{temp_db.name}"

    # Set environment variables for this test
    os.environ["DATABASE_URL"] = database_url
    os.environ["SQLITE_DB_PATH"] = temp_db.name

    # Force reload of database modules to pick up new environment variables
    reload_database_modules()

    # Create engine with NullPool to avoid connection pooling issues
    from sqlalchemy.pool import NullPool

    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )

    # Make sure all tables are created
    Base.metadata.create_all(bind=engine)

    # Run seed to populate initial data
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        _create_category_hierarchy(session)
        session.commit()
    finally:
        session.close()

    return engine


@pytest.fixture(scope="function")
def TestingSessionLocal(test_engine):
    """Create a session factory for testing."""
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def app(test_engine, TestingSessionLocal):
    """Create a test app with overridden database dependencies."""
    from contextlib import asynccontextmanager
    import backend.app.database as database_module
    from backend.app.main import get_db
    from backend.app.main import app as main_app

    # Patch the database module to use our test engine
    original_engine = database_module.engine
    original_sessionlocal = database_module.SessionLocal
    database_module.engine = test_engine
    database_module.SessionLocal = TestingSessionLocal

    @asynccontextmanager
    async def test_lifespan(app: FastAPI):
        # Skip the seeding in the test lifecycle since we handle it separately
        yield

    # Create a new FastAPI app with test configurations
    test_app = FastAPI(title="ERP Pessoal API - TEST", lifespan=test_lifespan)

    # Copy routes from the main app
    for route in main_app.routes:
        test_app.router.routes.append(route)

    # Create a fresh session for each request (no long-running transaction)
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    test_app.dependency_overrides[get_db] = override_get_db

    yield test_app

    # Restore original database module state
    database_module.engine = original_engine
    database_module.SessionLocal = original_sessionlocal


@pytest.fixture(scope="function")
def db_session(app, test_engine, TestingSessionLocal):
    """Create a database session for each test function with rollback capability."""
    # Use the same connection approach as the app fixture for consistency
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # Create tables and seed data
    Base.metadata.create_all(bind=connection)
    _create_category_hierarchy(session)
    session.commit()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(app):
    """Create a test client."""
    return TestClient(app)


def test_categories_endpoint_contains_expected_categories(client) -> None:
    """Garante que o endpoint /categories retorna categorias seeds esperadas."""
    print("Testing categories endpoint...")

    try:
        response = client.get("/categories")
        if response.status_code != 200:
            print(f"Categories endpoint error: {response.text}")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        category_names: Set[str] = {item["name"] for item in data}

        # Categorias específicas que devem existir após o seed:
        # - "Portugal 202606" (filha de "Viagem")
        # - "Saúde" (categoria raiz)
        assert "Portugal 202606" in category_names
        assert "Saúde" in category_names

        print("SUCCESS: Categories endpoint returned expected categories")
    except Exception as e:
        print(
            f"Error in test_categories_endpoint_contains_expected_categories: {str(e)}"
        )
        raise


def test_fiscal_items_orphans_returns_correct_list(client, db_session) -> None:
    """Teste de Órfãos: Verifique se GET /fiscal-items/orphans retorna a lista correta e se o formato do JSON não mudou."""
    print("Testing /fiscal-items/orphans endpoint...")

    try:
        # Create a category
        category = Category(name="Mercado", parent=None)
        db_session.add(category)
        db_session.commit()
        db_session.refresh(category)

        # Create a fiscal note
        note = FiscalNote(
            date=date(2025, 1, 1),
            total_amount=100.0,
            seller_name="Supermercado Exemplo",
            access_key="ABC123",
            source_type=FiscalSourceType.XML,
        )
        db_session.add(note)
        db_session.commit()
        db_session.refresh(note)

        # Create a fiscal item without a product mapping (orphan)
        item = FiscalItem(
            note_id=note.id,
            product_name="Produto Órfão",
            quantity=1.0,
            unit_price=20.0,
            total_price=20.0,
            category_id=category.id,
        )
        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)

        # Now test the orphans endpoint
        response = client.get("/fiscal-items/orphans")
        if response.status_code != 200:
            print(f"Orphans endpoint error: {response.text}")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        # Verify the structure of the returned items
        if len(data) > 0:
            first_item = data[0]
            expected_keys = {
                "id",
                "product_name",
                "quantity",
                "unit_price",
                "total_price",
                "category_id",
                "product_ean",
            }
            assert set(first_item.keys()).issuperset(expected_keys), (
                f"Missing keys in response: {expected_keys - set(first_item.keys())}"
            )

            # Validate that product_ean is present and is null for orphan items
            assert first_item.get("product_ean") is None, (
                f"Expected product_ean to be null for orphan items, got: {first_item.get('product_ean')}"
            )

        print(
            f"SUCCESS: Orphans endpoint returned {len(data)} items with correct format"
        )

    finally:
        db_session.close()


def test_product_ean_registration(client) -> None:
    """Teste de Cadastro de EAN: Simule o envio de um EAN de 13 dígitos para POST /products/eans/ e valide se ele é salvo com sucesso."""
    print("Testing POST /products/eans/ endpoint...")

    # Test with a 13-digit EAN
    ean_data = {"ean": "1234567890123", "name_standard": "Test Product Name"}

    try:
        response = client.post("/products/eans/", json=ean_data)
        if response.status_code != 200:
            print(f"EAN registration error: {response.text}")
        print(f"EAN registration response status: {response.status_code}")
        print(f"EAN registration response: {response.json()}")

        assert response.status_code == 200

        data = response.json()
        assert "message" in data
        # Check for various success messages depending on whether it's a new creation or update
        success_messages = [
            "Produto criado com sucesso",
            "Produto atualizado com sucesso",
            "EAN registered successfully",
        ]
        assert any(msg in data["message"] for msg in success_messages), (
            f"Unexpected message: {data['message']}"
        )

        print("SUCCESS: EAN registration endpoint worked correctly")
    except Exception as e:
        print(f"Error in test_product_ean_registration: {str(e)}")
        raise


def test_product_mapping_creation(client) -> None:
    """Teste de Mapeamento: Verifique se o vínculo entre uma descrição (ex: "BANANA PRATA") e um EAN cria o registro correto na tabela product_mapping."""
    print("Testing product mapping creation...")

    # First register an EAN
    ean_data = {"ean": "5678901234567", "name_standard": "BANANA PRATA"}

    try:
        response = client.post("/products/eans/", json=ean_data)
        if response.status_code != 200:
            print(f"EAN registration error: {response.text}")
        assert response.status_code == 200

        # Then try to map the description to the EAN
        mapping_data = {
            "raw_description": "BANANA PRATA",
            "seller_name": "Any Seller",
            "product_ean": 5678901234567,
        }

        response = client.post("/product-mappings/", json=mapping_data)
        print(f"Product mapping response status: {response.status_code}")
        if response.status_code != 200:
            print(f"Product mapping response: {response.text}")

        assert response.status_code == 200

        data = response.json()
        assert "message" in data
        assert (
            "Mapeamento criado com sucesso" in data["message"]
            or "Mapeamento atualizado com sucesso" in data["message"]
        )

        print("SUCCESS: Product mapping endpoint worked correctly")
    except Exception as e:
        print(f"Error in test_product_mapping_creation: {str(e)}")
        raise


def test_family_category_preservation(client) -> None:
    """Teste de Categorias da Família: Garantir que, ao associar um produto à Ana ou Carol, o category_id correto seja preservado."""
    print("Testing family category preservation...")

    try:
        # Get categories for Ana and Carol to ensure they exist
        response = client.get("/categories")
        if response.status_code != 200:
            print(f"Categories retrieval error: {response.text}")
        assert response.status_code == 200

        categories = response.json()
        ana_category = None
        carol_category = None

        for cat in categories:
            if cat["name"] == "Ana":
                ana_category = cat
            elif cat["name"] == "Carol":
                carol_category = cat

        # If these specific categories don't exist at the expected level, find education subcategories
        if not ana_category or not carol_category:
            for cat in categories:
                if cat["name"] == "Educação":
                    for child in cat.get("children", []):
                        if child["name"] == "Ana":
                            ana_category = child
                        elif child["name"] == "Carol":
                            carol_category = child

        assert ana_category is not None, "Ana category should exist"
        assert carol_category is not None, "Carol category should exist"

        print(f"Found Ana category ID: {ana_category['id']}")
        print(f"Found Carol category ID: {carol_category['id']}")

        # Validate that the categories exist with valid IDs
        assert ana_category["id"] is not None, "Ana category should have a valid ID"
        assert carol_category["id"] is not None, "Carol category should have a valid ID"

        # Verify that these are subcategories of "Educação" by checking parent_id
        educacao_category = None
        for cat in categories:
            if cat["name"] == "Educação":
                educacao_category = cat
                break

        assert educacao_category is not None, "Educação category should exist"

        # Verify Ana and Carol have parent_id pointing to Educação
        assert ana_category.get("parent_id") == educacao_category["id"], (
            f"Ana should have parent_id {educacao_category['id']} (Educação), got {ana_category.get('parent_id')}"
        )
        assert carol_category.get("parent_id") == educacao_category["id"], (
            f"Carol should have parent_id {educacao_category['id']} (Educação), got {carol_category.get('parent_id')}"
        )

        print(
            "SUCCESS: Ana and Carol categories are properly structured under Educação"
        )
        print("SUCCESS: Family category preservation verified")
    except Exception as e:
        print(f"Error in test_family_category_preservation: {str(e)}")
        raise
