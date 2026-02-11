from __future__ import annotations

import logging
import os
import re
from datetime import date
from typing import Generator, List, Optional

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from pydantic import BaseModel, HttpUrl

from .models import (
    BankTransaction,
    Category,
    FiscalItem,
    FiscalNote,
    FiscalSourceType,
)
from .schemas import CategoryOut, FiscalItemOut, FiscalNoteOut, TransactionCreate, TransactionOut
from .seed import get_session_factory, seed_categories
from .services.scraper_handler import ScraperImporter
from .services.xml_handler import ParsedNote, XMLProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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


@app.get("/health")
def health_check():
    """Health check endpoint to verify API availability."""
    return {"status": "ok", "message": "Backend is running"}


@app.on_event("startup")
def startup_event() -> None:
    """Garante que o banco tenha as categorias iniciais.

    Em vez de checar apenas a existência de arquivo físico, verificamos
    se a tabela de categorias está vazia. Se não houver nenhuma categoria,
    executamos o seed.
    """

    print(f"[startup] DATABASE_URL = {DATABASE_URL}")

    with SessionLocal() as db:
        first_category = db.query(Category.id).first()
        print(f"[startup] Primeira categoria encontrada: {first_category}")
        if first_category is None:
            print("[startup] Nenhuma categoria encontrada. Executando seed_categories...")
            seed_categories(DATABASE_URL)
        else:
            print("[startup] Categorias já existentes. Seed não será executado.")




@app.get("/categories", response_model=List[CategoryOut])
def list_categories(db: Session = Depends(get_db)) -> List[CategoryOut]:
    """Retorna todas as categorias cadastradas."""

    result = db.execute(select(Category).order_by(Category.name))
    categories: List[Category] = list(result.scalars().all())
    print(f"[categories] Total encontradas: {len(categories)}")
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
    logger.info(f"Transaction committed to database: ID {transaction.id}")
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


def _persist_parsed_note(
    parsed: ParsedNote, source_type: FiscalSourceType, db: Session
) -> FiscalNote:
    """Persiste uma nota e seus itens a partir de um ParsedNote."""

    note = FiscalNote(
        date=parsed.date,
        total_amount=parsed.total_amount,
        seller_name=parsed.seller_name,
        access_key=parsed.access_key,
        source_type=source_type,
    )
    db.add(note)
    db.flush()

    for item in parsed.items:
        fiscal_item = FiscalItem(
            note_id=note.id,
            product_name=item.name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.total_price,
            category_id=None,
        )
        db.add(fiscal_item)

    db.commit()
    logger.info(f"Fiscal note and items committed to database: ID {note.id}")
    db.refresh(note)
    return note


@app.post("/import/xml")
async def import_xml(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    """Importa uma nota a partir de um arquivo XML de NF-e/NFC-e."""

    content = await file.read()
    processor = XMLProcessor()
    parsed = processor.parse(content)

    note = _persist_parsed_note(parsed, FiscalSourceType.XML, db)

    return {
        "note_id": note.id,
        "items_count": len(parsed.items),
        "seller_name": note.seller_name,
        "total_amount": note.total_amount,
    }


class ImportUrlPayload(BaseModel):
    url: HttpUrl
    use_browser: bool = False


@app.post("/import/url")
def import_url(
    payload: ImportUrlPayload,
    db: Session = Depends(get_db),
) -> dict:
    """Importa uma nota a partir da URL de consulta da NFC-e."""

    importer = ScraperImporter()
    try:
        parsed = importer.import_from_url(
            str(payload.url),
            force_browser=payload.use_browser,
        )
    except ValueError as exc:
        # Erros de parsing/scraping são retornados como 422 para o cliente.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    note = _persist_parsed_note(parsed, FiscalSourceType.SCRAPING, db)

    return {
        "note_id": note.id,
        "items_count": len(parsed.items),
        "seller_name": note.seller_name,
        "total_amount": note.total_amount,
    }


@app.get("/fiscal-notes", response_model=List[FiscalNoteOut])
def list_fiscal_notes(
    date_from: Optional[date] = Query(
        default=None,
        description="Data inicial para filtragem (formato ISO YYYY-MM-DD).",
    ),
    date_to: Optional[date] = Query(
        default=None,
        description="Data final para filtragem (formato ISO YYYY-MM-DD).",
    ),
    seller_name: Optional[str] = Query(
        default=None,
        description="Nome parcial ou completo do estabelecimento para filtragem.",
    ),
    db: Session = Depends(get_db),
) -> List[FiscalNoteOut]:
    """Lista notas fiscais importadas com filtros opcionais."""
    
    stmt = select(FiscalNote).options(joinedload(FiscalNote.items)).order_by(FiscalNote.date.desc())
    
    if date_from is not None:
        stmt = stmt.where(FiscalNote.date >= date_from)
    
    if date_to is not None:
        stmt = stmt.where(FiscalNote.date <= date_to)
        
    if seller_name is not None:
        stmt = stmt.where(FiscalNote.seller_name.ilike(f"%{seller_name}%"))
    
    result = db.execute(stmt)
    notes = result.unique().scalars().all()
    
    return [FiscalNoteOut.model_validate(note) for note in notes]


@app.get("/fiscal-notes/{note_id}", response_model=FiscalNoteOut)
def get_fiscal_note(note_id: int, db: Session = Depends(get_db)) -> FiscalNoteOut:
    """Retorna os detalhes de uma nota fiscal específica, incluindo seus itens."""
    
    note = db.query(FiscalNote).options(joinedload(FiscalNote.items)).filter(FiscalNote.id == note_id).first()
    
    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nota fiscal com ID {note_id} não encontrada."
        )
    
    return FiscalNoteOut.model_validate(note)


@app.get("/fiscal-items")
def list_fiscal_items(
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> List[dict]:
    """Lista os itens fiscais mais recentes das notas importadas."""
    
    stmt = (
        select(FiscalItem, FiscalNote)
        .join(FiscalNote, FiscalItem.note_id == FiscalNote.id)
        .order_by(FiscalNote.date.desc(), FiscalItem.id.desc())
        .limit(limit)
    )
    
    result = db.execute(stmt)
    rows = result.all()
    
    items = []
    for fiscal_item, fiscal_note in rows:
        items.append({
            "id": fiscal_item.id,
            "product_name": fiscal_item.product_name,
            "quantity": fiscal_item.quantity,
            "unit_price": fiscal_item.unit_price,
            "total_price": fiscal_item.total_price,
            "category_id": fiscal_item.category_id,
            "note_id": fiscal_note.id,
            "note_date": fiscal_note.date.isoformat(),
            "seller_name": fiscal_note.seller_name,
        })
    
    return items


def normalize_product_name(name: str) -> str:
    """Normalize product name for comparison by removing special characters and converting to lowercase."""
    if not name:
        return ""
    # Remove special characters and convert to lowercase
    normalized = re.sub(r'[^\w\s]', ' ', name.lower())
    # Remove extra whitespaces
    normalized = ' '.join(normalized.split())
    return normalized


@app.get("/analytics/price-comparison")
def price_comparison(
    product_name: str = Query(..., description="Product name to search for"),
    db: Session = Depends(get_db),
) -> List[dict]:
    """Compare prices of a specific product across different markets over time."""
    
    # Normalize the search term
    normalized_search = normalize_product_name(product_name)
    
    # Find all fiscal items with similar product names
    stmt = (
        select(FiscalItem, FiscalNote)
        .join(FiscalNote, FiscalItem.note_id == FiscalNote.id)
        .where(func.lower(FiscalItem.product_name).contains(normalized_search))
        .order_by(FiscalNote.date)
    )
    
    result = db.execute(stmt)
    rows = result.all()
    
    # Group items by normalized product name
    items = []
    for fiscal_item, fiscal_note in rows:
        normalized_item_name = normalize_product_name(fiscal_item.product_name)
        
        # Only include if the normalized name contains our search term
        if normalized_search in normalized_item_name:
            items.append({
                "product_name": fiscal_item.product_name,
                "normalized_name": normalized_item_name,
                "unit_price": fiscal_item.unit_price,
                "date": fiscal_note.date.isoformat(),
                "seller_name": fiscal_note.seller_name,
            })
    
    return items


__all__ = ["app", "get_db", "DATABASE_URL", "SQLITE_DB_PATH"]

