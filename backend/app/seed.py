from __future__ import annotations

from typing import Dict, List

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from .models import Base, Category


class SeedError(Exception):
    """Erro de alto nível para problemas durante o seed de dados."""


def get_engine(database_url: str) -> "create_engine":
    """Cria uma engine SQLAlchemy.

    Args:
        database_url: URL de conexão do banco de dados.

    Returns:
        Instância de engine SQLAlchemy.
    """

    return create_engine(database_url, echo=False, future=True)


def get_session_factory(database_url: str) -> sessionmaker[Session]:
    """Cria uma fábrica de sessões vinculada à engine.

    Args:
        database_url: URL de conexão do banco de dados.

    Returns:
        Um sessionmaker tipado para `Session`.
    """

    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def _create_category_hierarchy(session: Session) -> None:
    """Cria a hierarquia fixa de categorias no banco.

    Esta função não deve ser exposta diretamente fora deste módulo para evitar
    uso sem controle de transação.

    Args:
        session: Sessão ativa do SQLAlchemy.
    """

    roots_with_children: Dict[str, List[str]] = {
        "Ajuda família": ["Ajuda Bruna Isabela", "Família Dadi"],
        "Despesas pessoais": [
            "Ana - Cuidados pessoais",
            "Carol - Cuidados pessoais",
            "Casa - Cuidados pessoais",
            "Eduardo - Cuidados pessoais",
        ],
        "Educação": ["Carol", "Ana", "Eduardo"],
        "Moradia": [
            "água",
            "Internet + Tv + celulares",
            "Iptu",
            "Luz",
            "manutenções",
            "Mobília",
        ],
        "Saúde": ["medicamentos", "profissionais saúde", "Suplementos"],
        "Transporte": ["Gasolina", "manutenção carro", "seguro", "Tags pedágio"],
        "Trabalho": ["Almoço", "bike e etc", "passagens"],
        "Viagem": [
            "Natal",
            "Portugal 202508",
            "Portugal 202606",
            "Portugal-202502",
            "São Pedro 202410",
        ],
    }

    outros_root = Category(name="Outros", parent=None)
    session.add(outros_root)
    session.flush()

    outros_children: List[str] = [
        "Assinaturas e serviços",
        "Bares e restaurantes",
        "Despesas reembolsadas",
        "Impostos e Taxas",
        "Cinema e aluguel",
        "Mercado",
        "Diversos",
        "Presentes e doações (dízimos, ofertas, Presentes)",
    ]
    for child_name in outros_children:
        session.add(Category(name=child_name, parent=outros_root))

    for root_name, children in roots_with_children.items():
        root_category = Category(name=root_name, parent=None)
        session.add(root_category)
        session.flush()
        for child_name in children:
            session.add(Category(name=child_name, parent=root_category))


def seed_categories(database_url: str) -> None:
    """Popula a tabela de categorias com a estrutura fixa definida.

    Args:
        database_url: URL de conexão do banco de dados.

    Raises:
        SeedError: Em caso de falha na transação de seed.
    """

    session_factory = get_session_factory(database_url)

    try:
        with session_factory() as session:
            _create_category_hierarchy(session)
            session.commit()
    except SQLAlchemyError as exc:
        raise SeedError("Falha ao executar seed de categorias.") from exc


__all__ = ["seed_categories", "SeedError", "get_session_factory", "get_engine"]

