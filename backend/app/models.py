from __future__ import annotations

from datetime import date
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarativa para todos os modelos ORM."""


class FiscalSourceType(str, Enum):
    """Enum para origem da nota fiscal."""

    XML = "XML"
    SCRAPING = "SCRAPING"


class Category(Base):
    """Categoria de classificação financeira, com suporte a hierarquia.

    Attributes:
        id: Identificador único da categoria.
        name: Nome da categoria.
        parent_id: Referência opcional para a categoria pai.
        parent: Relação ORM com a categoria pai.
        children: Relação ORM com as categorias filhas.
    """

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=False)
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("categories.id"), nullable=True
    )

    parent: Mapped[Optional["Category"]] = relationship(
        "Category", remote_side="Category.id", back_populates="children"
    )
    children: Mapped[List["Category"]] = relationship(
        "Category", back_populates="parent", cascade="all, delete-orphan"
    )


class BankTransaction(Base):
    """Transação bancária básica.

    Attributes:
        id: Identificador único da transação.
        date: Data da transação.
        description: Descrição textual.
        amount: Valor monetário (positivo ou negativo).
        category_id: Chave estrangeira para `Category`.
        is_reconciled: Indica se a transação já foi conciliada.
        category: Relação ORM com `Category`.
    """

    __tablename__ = "bank_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    category_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("categories.id"), nullable=True
    )
    is_reconciled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    category: Mapped[Optional[Category]] = relationship("Category")

    __table_args__ = (
        CheckConstraint("amount <> 0", name="ck_bank_transactions_amount_non_zero"),
    )


class FiscalNote(Base):
    """Nota fiscal consolidada.

    Attributes:
        id: Identificador único da nota.
        date: Data da emissão.
        total_amount: Valor total da nota.
        seller_name: Nome do emissor/vendedor.
        access_key: Chave de acesso única.
        source_type: Origem da nota (XML ou Scraping).
        items: Relação ORM com itens da nota.
    """

    __tablename__ = "fiscal_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    seller_name: Mapped[str] = mapped_column(String(255), nullable=False)
    access_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    source_type: Mapped[FiscalSourceType] = mapped_column(
        SAEnum(FiscalSourceType), nullable=False
    )

    items: Mapped[List["FiscalItem"]] = relationship(
        "FiscalItem", back_populates="note", cascade="all, delete-orphan"
    )


class ProductMaster(Base):
    """Cadastro único de produtos por EAN.

    Attributes:
        ean: Código EAN do produto (chave primária).
        name_standard: Nome amigável padronizado do produto.
        category_id: Chave estrangeira para `Category`.
    """

    __tablename__ = "products_master"

    ean: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name_standard: Mapped[str] = mapped_column(String(255), nullable=False)
    category_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("categories.id"), nullable=True
    )

    category: Mapped[Optional[Category]] = relationship("Category")


class ProductMapping(Base):
    """Mapeamento entre descrições brutas e produtos identificados.

    Attributes:
        id: Identificador único do mapeamento.
        raw_description: Descrição original do produto na nota fiscal.
        seller_name: Nome do vendedor/mercado.
        product_ean: Chave estrangeira para o produto master.
    """

    __tablename__ = "product_mapping"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    raw_description: Mapped[str] = mapped_column(String(255), nullable=False)
    seller_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_ean: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("products_master.ean"), nullable=False
    )

    product: Mapped[ProductMaster] = relationship("ProductMaster")


class FiscalItem(Base):
    """Item pertencente a uma nota fiscal.

    Attributes:
        id: Identificador único do item.
        note_id: Chave estrangeira para a nota fiscal.
        product_name: Nome do produto.
        quantity: Quantidade adquirida.
        unit_price: Preço unitário.
        total_price: Preço total do item.
        category_id: Chave estrangeira para `Category`.
        product_ean: Chave estrangeira opcional para products_master (para vínculos futuros).
        note: Relação ORM com `FiscalNote`.
        category: Relação ORM com `Category`.
    """

    __tablename__ = "fiscal_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    note_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("fiscal_notes.id"), nullable=False
    )
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    total_price: Mapped[float] = mapped_column(Float, nullable=False)
    category_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("categories.id"), nullable=True
    )
    product_ean: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("products_master.ean"), nullable=True
    )

    note: Mapped[FiscalNote] = relationship("FiscalNote", back_populates="items")
    category: Mapped[Optional[Category]] = relationship("Category")
    product: Mapped[Optional[ProductMaster]] = relationship("ProductMaster")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_fiscal_items_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_fiscal_items_unit_price_non_neg"),
        CheckConstraint("total_price >= 0", name="ck_fiscal_items_total_price_non_neg"),
    )

