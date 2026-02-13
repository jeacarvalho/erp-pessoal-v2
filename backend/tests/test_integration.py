from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest
import os
from unittest.mock import patch

# Temporarily set the DATABASE_URL environment variable to use in-memory database
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from backend.app.models import Base, Category, ProductMaster, ProductMapping, FiscalNote, FiscalItem
from backend.app.main import app
from backend.app.database import engine, SessionLocal


# Setup database in memory for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="module")
def client():
    # Create tables in the in-memory database
    Base.metadata.create_all(bind=test_engine)
    
    # Mock the startup event to avoid database operations during startup
    with patch('backend.app.main.SessionLocal'):
        with TestClient(app) as c:
            yield c
    
    # Clean up after tests
    Base.metadata.drop_all(bind=test_engine)


def test_complete_item_lifecycle(client):
    """
    Integration test validating the complete lifecycle of an item.
    This test ensures that the system properly maps items from fiscal notes to registered products
    using the product mapping mechanism.
    """
    
    # Step 1: Create Context - Create a category (ex: "Eduardo - Cuidados Pessoais", ID 1)
    category_response = client.post(
        "/categories/",
        json={
            "id": 1,
            "name": "Eduardo - Cuidados Pessoais",
            "parent_id": None
        }
    )
    assert category_response.status_code == 200, f"Failed to create category: {category_response.text}"
    category_data = category_response.json()
    assert category_data["name"] == "Eduardo - Cuidados Pessoais"
    assert category_data["id"] == 1
    
    # Step 2: Register Master - POST /products/eans/ to register "Desodorante XPTO" with EAN 7891234567890
    product_response = client.post(
        "/products/eans/",
        json={
            "ean": "7891234567890",
            "name_standard": "Desodorante XPTO",
            "category_id": 1,
            "price": 15.99
        }
    )
    assert product_response.status_code == 200, f"Failed to create product: {product_response.text}"
    product_data = product_response.json()
    assert product_data["ean"] == "7891234567890"
    assert product_data["name"] == "Desodorante XPTO"
    
    # Step 3: Intelligence Mapping - POST /product-mappings/ teaching the system that 
    # at "Supermercado Real", description "DESODORANTE XPTO 150ML" corresponds to the registered EAN
    mapping_response = client.post(
        "/product-mappings/",
        json={
            "source_description": "DESODORANTE XPTO 150ML",
            "target_ean": "7891234567890",
            "store_name": "Supermercado Real"
        }
    )
    assert mapping_response.status_code == 200, f"Failed to create product mapping: {mapping_response.text}"
    mapping_data = mapping_response.json()
    assert mapping_data["source_description"] == "DESODORANTE XPTO 150ML"
    assert mapping_data["target_ean"] == "7891234567890"
    assert mapping_data["store_name"] == "Supermercado Real"
    
    # Step 4: The Ultimate Test (Import Process)
    # Create a FiscalNote
    fiscal_note_response = client.post(
        "/fiscal-notes/",
        json={
            "number": "12345",
            "serie": "1",
            "cnpj": "12345678000195",
            "emission_date": "2023-01-01T00:00:00",
            "total_value": 15.99
        }
    )
    assert fiscal_note_response.status_code == 200, f"Failed to create fiscal note: {fiscal_note_response.text}"
    fiscal_note_data = fiscal_note_response.json()
    fiscal_note_id = fiscal_note_data["id"]
    assert fiscal_note_data["number"] == "12345"
    
    # Add a FiscalItem with the exact description "DESODORANTE XPTO 150ML"
    fiscal_item_response = client.post(
        f"/fiscal-notes/{fiscal_note_id}/items/",
        json={
            "description": "DESODORANTE XPTO 150ML",
            "quantity": 1,
            "unit_value": 15.99,
            "total_value": 15.99
        }
    )
    assert fiscal_item_response.status_code == 200, f"Failed to create fiscal item: {fiscal_item_response.text}"
    fiscal_item_data = fiscal_item_response.json()
    
    # Critical Assertion: Verify that the backend automatically filled the product_ean column
    # with the value 7891234567890 when saving the item
    assert "product_ean" in fiscal_item_data, "product_ean field is missing from fiscal item response"
    assert fiscal_item_data["product_ean"] == "7891234567890", \
        f"Expected product_ean to be '7891234567890', but got '{fiscal_item_data.get('product_ean')}'"
    
    print("Integration test passed: The system correctly mapped the fiscal item to the registered product EAN!")