from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class CategoryOut(BaseModel):
    """Schema de saída para categorias."""

    id: int
    name: str
    parent_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class FiscalItemOut(BaseModel):
    """Schema de saída para itens fiscais."""

    id: int
    product_name: str
    quantity: float
    unit_price: float
    total_price: float
    category_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class FiscalNoteOut(BaseModel):
    """Schema de saída para notas fiscais com seus itens."""

    id: int
    date: date
    total_amount: float
    seller_name: str
    access_key: str
    source_type: str
    items: List[FiscalItemOut]

    model_config = ConfigDict(from_attributes=True)


class TransactionCreate(BaseModel):
    """Schema de entrada para criação de transações bancárias."""

    date: date
    description: str
    amount: float
    category_id: Optional[int] = None
    is_reconciled: bool = False


class TransactionOut(BaseModel):
    """Schema de saída para transações, incluindo dados da categoria associada."""

    id: int
    date: date
    description: str
    amount: float
    is_reconciled: bool
    category: Optional[CategoryOut] = None
    category_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ProductMappingCreate(BaseModel):
    """Schema de entrada para criação de mapeamentos de produtos."""

    raw_description: str
    seller_name: str
    product_ean: int

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "CategoryOut",
    "FiscalItemOut",
    "FiscalNoteOut",
    "TransactionCreate",
    "TransactionOut",
    "ProductMappingCreate",
]

