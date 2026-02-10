from __future__ import annotations

from datetime import date
from typing import List

from sqlalchemy.orm import Session

from backend.app.models import (
    Base,
    Category,
    FiscalItem,
    FiscalNote,
    FiscalSourceType,
)
from backend.app.seed import get_engine, get_session_factory, seed_categories


def _create_in_memory_session() -> Session:
    """Cria uma sessão em banco SQLite em memória para testes.

    Returns:
        Sessão SQLAlchemy conectada a um banco SQLite em memória.
    """

    engine = get_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = get_session_factory("sqlite+pysqlite:///:memory:")
    return session_factory()


def test_category_hierarchy_seed_creates_expected_structure() -> None:
    """Garante que a hierarquia de categorias foi criada corretamente."""

    database_url = "sqlite+pysqlite:///:memory:"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)

    seed_categories(database_url)
    session_factory = get_session_factory(database_url)

    with session_factory() as session:
        roots: List[Category] = (
            session.query(Category)
            .filter(Category.parent_id.is_(None))
            .order_by(Category.name)
            .all()
        )
        root_names = {root.name for root in roots}

        expected_roots = {
            "Ajuda família",
            "Despesas pessoais",
            "Educação",
            "Moradia",
            "Saúde",
            "Transporte",
            "Trabalho",
            "Viagem",
            "Outros",
        }
        assert expected_roots.issubset(root_names)

        ajuda_familia = next(r for r in roots if r.name == "Ajuda família")
        ajuda_children = {child.name for child in ajuda_familia.children}
        assert ajuda_children == {"Ajuda Bruna Isabela", "Família Dadi"}

        moradia = next(r for r in roots if r.name == "Moradia")
        moradia_children = {child.name for child in moradia.children}
        assert moradia_children == {
            "água",
            "Internet + Tv + celulares",
            "Iptu",
            "Luz",
            "manutenções",
            "Mobília",
        }

        outros = next(r for r in roots if r.name == "Outros")
        outros_children = {child.name for child in outros.children}
        assert "Assinaturas e serviços" in outros_children
        assert "Presentes e doações (dízimos, ofertas, Presentes)" in outros_children


def test_fiscal_item_association_with_note_and_category() -> None:
    """Verifica se FiscalItem associa corretamente com FiscalNote e Category."""

    database_url = "sqlite+pysqlite:///:memory:"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    session_factory = get_session_factory(database_url)

    with session_factory() as session:
        categoria_mercado = Category(name="Mercado", parent=None)
        session.add(categoria_mercado)
        session.flush()

        nota = FiscalNote(
            date=date(2025, 1, 1),
            total_amount=100.0,
            seller_name="Supermercado Exemplo",
            access_key="ABC123",
            source_type=FiscalSourceType.XML,
        )
        session.add(nota)
        session.flush()

        item = FiscalItem(
            note_id=nota.id,
            product_name="Arroz 5kg",
            quantity=1.0,
            unit_price=20.0,
            total_price=20.0,
            category_id=categoria_mercado.id,
        )
        session.add(item)
        session.commit()

        fetched_item: FiscalItem = session.query(FiscalItem).first()  # type: ignore[assignment]
        assert fetched_item is not None
        assert fetched_item.note is not None
        assert fetched_item.note.access_key == "ABC123"
        assert fetched_item.category is not None
        assert fetched_item.category.name == "Mercado"

