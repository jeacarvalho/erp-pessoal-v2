from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CategoryOut(BaseModel):
    """Schema de saída para categorias."""

    id: int
    name: str
    parent_id: Optional[int] = None

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


__all__ = [
    "CategoryOut",
    "TransactionCreate",
    "TransactionOut",
]

