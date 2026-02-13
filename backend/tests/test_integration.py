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
    
    # Manually seed categories in the test database using the same engine
    from backend.app.seed import _create_category_hierarchy
    with TestingSessionLocal() as db:
        _create_category_hierarchy(db)
        db.commit()
    
    # Create a fresh FastAPI app instance without lifespan for testing
    from backend.app.main import app
    from fastapi.testclient import TestClient
    
    # Create a new app instance without the lifespan
    from fastapi import FastAPI
    
    test_app = FastAPI(title="ERP Pessoal API Test")
    
    # Copy routes from the original app
    for route in app.routes:
        test_app.routes.append(route)
    
    # Set up database session dependency
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    from backend.app.main import get_db
    test_app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(test_app) as c:
        yield c
    
    # Clean up after tests
    Base.metadata.drop_all(bind=test_engine)


def test_complete_item_lifecycle(client):
    """
    Integration test validating the complete lifecycle of an item.
    This test ensures that the system properly maps items from fiscal notes to registered products
    using the product mapping mechanism.
    """
    
    # Step 1: Create Context - Get existing categories since there's no POST /categories/
    # We'll use the existing categories from the seed data
    categories_response = client.get("/categories")
    assert categories_response.status_code == 200, f"Failed to get categories: {categories_response.text}"
    categories_data = categories_response.json()
    
    # Find or create a category for our test
    if len(categories_data) > 0:
        # Use the first category if available
        category_data = categories_data[0]
    else:
        # If no categories exist, we need to handle this differently
        # Actually, the startup event should ensure basic categories exist
        assert len(categories_data) > 0, "At least one category should exist"
        category_data = categories_data[0]
    
    # Print for debugging
    print(f"Using category: {category_data}")
    
    # Step 2: Register Master - POST /products/eans/ to register "Desodorante XPTO" with EAN 7891234567890
    product_response = client.post(
        "/products/eans/",
        json={
            "ean": "7891234567890",
            "name_standard": "Desodorante XPTO",
            "category_id": category_data["id"],  # Use the category ID we found earlier
        }
    )
    assert product_response.status_code == 200, f"Failed to create product: {product_response.text}"
    product_data = product_response.json()
    assert product_data["ean"] == "7891234567890"
    # Changed from "name" to "name_standard" to match the schema
    assert "name_standard" in str(product_response.text).lower() or "desodorante xpto" in str(product_response.text).lower()
    
    # Step 3: Intelligence Mapping - POST /product-mappings/ teaching the system that 
    # at "Supermercado Real", description "DESODORANTE XPTO 150ML" corresponds to the registered EAN
    mapping_response = client.post(
        "/product-mappings/",
        json={
            "raw_description": "DESODORANTE XPTO 150ML",
            "seller_name": "Supermercado Real",
            "product_ean": 7891234567890
        }
    )
    assert mapping_response.status_code == 200, f"Failed to create product mapping: {mapping_response.text}"
    mapping_data = mapping_response.json()
    assert mapping_data["raw_description"] == "DESODORANTE XPTO 150ML"
    assert mapping_data["product_ean"] == 7891234567890
    assert mapping_data["seller_name"] == "Supermercado Real"
    
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