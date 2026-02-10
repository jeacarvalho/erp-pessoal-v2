from __future__ import annotations

import os
from typing import Generator, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import BankTransaction, Category
from .schemas import CategoryOut, TransactionCreate, TransactionOut
from .seed import get_session_factory, seed_categories


# Configuração de banco de dados
DATABASE_URL: str = os.getenv("DATABASE_URL") or f"sqlite+pysqlite:///{os.getenv('SQLITE_DB_PATH', 'app.db')}"
SQLITE_DB_PATH: Optional[str] = None

if not os.getenv("DATABASE_URL"):
    # Apenas faz sentido falar em arquivo físico para SQLite.
    SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "app.db")

SessionLocal = get_session_factory(DATABASE_URL)


def get_db() -> Generator[Session, None, None]:
    """Dependência de sessão de banco para os endpoints."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI(title="ERP Pessoal API")


@app.on_event("startup")
def startup_event() -> None:
    """Evento de startup para garantir seed inicial de categorias.

    A ideia é executar o seed apenas quando o banco for novo. Para SQLite,
    isso é feito verificando se o arquivo físico já existe. Para outros
    bancos (caso sejam usados no futuro), o seed é executado sempre.
    """

    if SQLITE_DB_PATH:
        # Banco SQLite baseado em arquivo: só semeia se o arquivo ainda não existir.
        if not os.path.exists(SQLITE_DB_PATH):
            seed_categories(DATABASE_URL)
    else:
        # Para outros tipos de URL, executa o seed sem checagem de arquivo.
        seed_categories(DATABASE_URL)


@app.get("/categories", response_model=List[CategoryOut])
def list_categories(db: Session = Depends(get_db)) -> List[CategoryOut]:
    """Retorna todas as categorias cadastradas."""

    result = db.execute(select(Category).order_by(Category.name))
    categories: List[Category] = list(result.scalars().all())
    return [CategoryOut.model_validate(cat) for cat in categories]


@app.get("/categories/tree")
def list_categories_tree(db: Session = Depends(get_db)) -> List[dict]:
    """Retorna categorias organizadas de forma hierárquica (Pai -> Filhos).

    Endpoint opcional, retornando uma estrutura simples de árvore.
    """

    result = db.execute(select(Category))
    categories: List[Category] = list(result.scalars().all())

    # Mapeia id -> nó da árvore
    node_map: dict[int, dict] = {}
    for cat in categories:
        node_map[cat.id] = {
            "id": cat.id,
            "name": cat.name,
            "parent_id": cat.parent_id,
            "children": [],
        }

    roots: List[dict] = []
    for cat in categories:
        node = node_map[cat.id]
        if cat.parent_id is None:
            roots.append(node)
        else:
            parent_node = node_map.get(cat.parent_id)
            if parent_node is not None:
                parent_node["children"].append(node)

    return roots


@app.post(
    "/transactions",
    response_model=TransactionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
) -> TransactionOut:
    """Cria um lançamento bancário vinculado a uma categoria."""

    if payload.category_id is not None:
        category = db.get(Category, payload.category_id)
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Categoria informada não existe.",
            )

    transaction = BankTransaction(
        date=payload.date,
        description=payload.description,
        amount=payload.amount,
        category_id=payload.category_id,
        is_reconciled=payload.is_reconciled,
    )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return TransactionOut.model_validate(transaction)


@app.get("/transactions", response_model=List[TransactionOut])
def list_transactions(
    category_id: Optional[int] = Query(
        default=None,
        description="Filtra transações por category_id, se informado.",
    ),
    db: Session = Depends(get_db),
) -> List[TransactionOut]:
    """Lista transações, com suporte a filtro por categoria."""

    stmt = select(BankTransaction).order_by(BankTransaction.date.desc())
    if category_id is not None:
        stmt = stmt.where(BankTransaction.category_id == category_id)

    result = db.execute(stmt)
    transactions: List[BankTransaction] = list(result.scalars().all())
    return [TransactionOut.model_validate(tx) for tx in transactions]


__all__ = ["app", "get_db", "DATABASE_URL", "SQLITE_DB_PATH"]

