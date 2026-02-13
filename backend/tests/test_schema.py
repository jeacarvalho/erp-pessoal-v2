from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy import create_engine
from backend.app.models import Base, FiscalItem, ProductMaster


def test_fiscal_items_table_has_required_columns():
    """Verify that fiscal_items table has exactly the required columns including product_ean."""
    # Using in-memory database for tests
    engine = create_engine("sqlite+pysqlite:///:memory:", echo=True)
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    
    columns = inspector.get_columns('fiscal_items')
    column_names = [col['name'] for col in columns]
    
    print(f"Fiscal items columns: {column_names}")
    
    # Check for required columns including the new product_ean
    required_columns = [
        'id', 'note_id', 'product_name', 'quantity', 'unit_price', 
        'total_price', 'category_id', 'product_ean'
    ]
    
    for col in required_columns:
        assert col in column_names, f"Column {col} missing from fiscal_items table"
    
    print("SUCCESS: All required columns found in fiscal_items table")


def test_products_master_uses_ean_as_primary_key():
    """Validate that products_master uses ean as primary key instead of id."""
    # Using in-memory database for tests
    engine = create_engine("sqlite+pysqlite:///:memory:", echo=True)
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    
    columns = inspector.get_columns('products_master')
    column_info = {}
    for col in columns:
        column_info[col['name']] = col
    
    print(f"Products master columns: {list(column_info.keys())}")
    
    # Check that ean exists and is primary key
    assert 'ean' in column_info, "Column 'ean' missing from products_master table"
    assert column_info['ean']['primary_key'], "'ean' should be a primary key in products_master"
    
    # Verify 'id' is not primary key if it exists
    if 'id' in column_info:
        assert not column_info['id']['primary_key'], "'id' should not be primary key in products_master when 'ean' exists"
    
    print("SUCCESS: products_master uses ean as primary key")