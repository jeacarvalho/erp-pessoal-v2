from __future__ import annotations
import time
import logging
import os
import re
from datetime import date, datetime
from typing import AsyncGenerator, List, Optional

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from pydantic import BaseModel, HttpUrl

from .models import (
    BankTransaction,
    Category,
    FiscalItem,
    FiscalNote,
    FiscalSourceType,
    ProductMapping,
    ProductMaster,
)
from .schemas import (
    CategoryOut,
    FiscalItemOut,
    FiscalNoteOut,
    TransactionCreate,
    TransactionOut,
    ProductMappingCreate,
    ProductMasterCreate,
)
from .seed import get_session_factory, seed_categories
from .services.scraper_handler import ScraperImporter
from .services.xml_handler import ParsedNote, XMLProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Configuração de banco de dados
DATABASE_URL: str = (
    os.getenv("DATABASE_URL")
    or f"sqlite+pysqlite:///{os.getenv('SQLITE_DB_PATH', '../data/sqlite/app.db')}"
)
SQLITE_DB_PATH: Optional[str] = None

if not os.getenv("DATABASE_URL"):
    # Apenas faz sentido falar em arquivo físico para SQLite.
    SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "../data/sqlite/app.db")

SessionLocal = get_session_factory(DATABASE_URL)


def get_db() -> Generator[Session, None, None]:
    """Dependência de sessão de banco para os endpoints."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


from contextlib import asynccontextmanager


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Garante que o banco tenha as categorias iniciais.

    Em vez de checar apenas a existência de arquivo físico, verificamos
    se a tabela de categorias está vazia. Se não houver nenhuma categoria,
    executamos o seed.
    """

    print(f"[lifespan] DATABASE_URL = {DATABASE_URL}")

    # Create tables in the database
    from .models import Base
    from .database import engine

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        first_category = db.query(Category.id).first()
        print(f"[lifespan] Primeira categoria encontrada: {first_category}")
        if first_category is None:
            print(
                "[lifespan] Nenhuma categoria encontrada. Executando seed_categories..."
            )
            seed_categories(DATABASE_URL)
        else:
            print("[lifespan] Categorias já existentes. Seed não será executado.")

    yield  # Aqui o app fica disponível para receber requisições

    # Código após o yield é executado quando o app é desligado
    print("[lifespan] Encerrando aplicação...")


app = FastAPI(title="ERP Pessoal API", lifespan=lifespan)

# Configurar CORS para permitir acesso do frontend (incluindo dispositivos móveis na rede local)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"
    ],  # Permite qualquer origem (adequado para desenvolvimento local)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Health check endpoint to verify API availability."""
    return {"status": "ok", "message": "Backend is running"}


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

    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Nota fiscal já importada. A chave de acesso '{parsed.access_key}' já existe no sistema.",
        ) from exc

    for item in parsed.items:
        # Verifica se já existe um mapeamento para este produto
        product_mapping = db.execute(
            select(ProductMapping).where(
                (ProductMapping.raw_description == item.name)
                & (ProductMapping.seller_name == parsed.seller_name)
            )
        ).scalar_one_or_none()

        # Prioritizes EAN from XML, falls back to product mapping if XML EAN is not available
        product_ean = item.ean
        if product_ean is None and product_mapping:
            product_ean = product_mapping.product_ean
            logger.info(
                f"Vínculo automático encontrado para '{item.name}' no vendedor '{parsed.seller_name}': EAN {product_ean}"
            )
        elif product_ean:
            logger.info(f"EAN encontrado no XML para '{item.name}': {product_ean}")
        else:
            logger.info(
                f"Item sem EAN, aguardando mapeamento manual: '{item.name}' no vendedor '{parsed.seller_name}'"
            )

        fiscal_item = FiscalItem(
            note_id=note.id,
            product_name=item.name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.total_price,
            category_id=None,
            product_ean=product_ean,
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


@app.post("/import/restore-from-backup")
def restore_from_backup(db: Session = Depends(get_db)) -> dict:
    """Restaura todas as notas a partir do arquivo de backup de URLs processadas."""

    import json
    import os

    backup_file_path = "../data/processed_urls_backup.json"

    # Check if backup file exists
    if not os.path.exists(backup_file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo de backup de URLs não encontrado.",
        )

    # Load URLs from backup file
    try:
        with open(backup_file_path, "r", encoding="utf-8") as f:
            urls = json.load(f)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro ao ler o arquivo de backup: {str(e)}",
        )

    if not urls:
        return {
            "message": "Nenhuma URL encontrada no arquivo de backup.",
            "total_urls": 0,
            "restored_count": 0,
        }

    # Import each URL using the scraper importer directly
    restored_count = 0
    errors = []

    importer = ScraperImporter()

    for url in urls:
        try:
            # Import the URL directly using the scraper handler
            parsed = importer.import_from_url(str(url), force_browser=False)
            time.sleep(5)
            # Persist the parsed note to the database
            note = _persist_parsed_note(parsed, FiscalSourceType.SCRAPING, db)
            restored_count += 1

        except Exception as e:
            errors.append({"url": url, "error": str(e)})

    return {
        "message": f"Processo de restauração concluído. {restored_count} de {len(urls)} URLs restauradas.",
        "total_urls": len(urls),
        "restored_count": restored_count,
        "errors": errors,
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

    stmt = (
        select(FiscalNote)
        .options(joinedload(FiscalNote.items))
        .order_by(FiscalNote.date.desc())
    )

    if date_from is not None:
        stmt = stmt.where(FiscalNote.date >= date_from)

    if date_to is not None:
        stmt = stmt.where(FiscalNote.date <= date_to)

    if seller_name is not None:
        stmt = stmt.where(FiscalNote.seller_name.ilike(f"%{seller_name}%"))

    result = db.execute(stmt)
    notes = result.unique().scalars().all()

    return [FiscalNoteOut.model_validate(note) for note in notes]


class FiscalNoteCreate(BaseModel):
    number: str
    serie: str
    cnpj: str
    emission_date: datetime
    total_value: float
    seller_name: Optional[str] = None
    access_key: Optional[str] = None


class FiscalItemCreate(BaseModel):
    description: str
    quantity: float
    unit_value: float
    total_value: float
    product_ean: Optional[str] = None


@app.post("/fiscal-notes", response_model=FiscalNoteOut)
def create_fiscal_note(
    note_data: FiscalNoteCreate, db: Session = Depends(get_db)
) -> FiscalNoteOut:
    """Cria uma nova nota fiscal."""
    # Create the fiscal note
    note = FiscalNote(
        date=note_data.emission_date.date(),
        total_amount=note_data.total_value,
        seller_name=note_data.seller_name or "Unknown Seller",
        access_key=note_data.access_key or f"KEY_{note_data.number}",
        source_type=FiscalSourceType.SCRAPING,  # Using SCRAPING as manual entry type
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    return FiscalNoteOut.model_validate(note)


@app.post("/fiscal-notes/{note_id}/items", response_model=FiscalItemOut)
def create_fiscal_item(
    note_id: int, item_data: FiscalItemCreate, db: Session = Depends(get_db)
) -> FiscalItemOut:
    """Cria um novo item fiscal associado a uma nota fiscal."""
    # Check if the note exists
    note = db.query(FiscalNote).filter(FiscalNote.id == note_id).first()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nota fiscal com ID {note_id} não encontrada.",
        )

    # Check if there's a product mapping for this description and seller
    product_mapping = db.execute(
        select(ProductMapping).where(
            (ProductMapping.raw_description == item_data.description)
            & (ProductMapping.seller_name == note.seller_name)
        )
    ).scalar_one_or_none()

    product_ean = item_data.product_ean
    if not product_ean and product_mapping:
        product_ean = str(product_mapping.product_ean)  # Convert to string

    # Create the fiscal item
    fiscal_item = FiscalItem(
        note_id=note_id,
        product_name=item_data.description,
        quantity=item_data.quantity,
        unit_price=item_data.unit_value,
        total_price=item_data.total_value,
        category_id=None,
        product_ean=product_ean,
    )

    db.add(fiscal_item)
    db.commit()
    db.refresh(fiscal_item)

    # Return the created item
    return FiscalItemOut.model_validate(fiscal_item)


@app.get("/fiscal-notes/{note_id}", response_model=FiscalNoteOut)
def get_fiscal_note(note_id: int, db: Session = Depends(get_db)) -> FiscalNoteOut:
    """Retorna os detalhes de uma nota fiscal específica, incluindo seus itens."""

    note = (
        db.query(FiscalNote)
        .options(joinedload(FiscalNote.items))
        .filter(FiscalNote.id == note_id)
        .first()
    )

    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nota fiscal com ID {note_id} não encontrada.",
        )

    return FiscalNoteOut.model_validate(note)


@app.get("/fiscal-items")
def list_fiscal_items(
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> List[dict]:
    """Lista os itens fiscais mais recentes das notas importadas."""

    # Log para mostrar o caminho real do banco de dados
    logger.info(f"[fiscal-items] Caminho real do banco de dados: {DATABASE_URL}")
    if SQLITE_DB_PATH:
        logger.info(
            f"[fiscal-items] Caminho físico do banco de dados: {os.path.abspath(SQLITE_DB_PATH)}"
        )

    stmt = (
        select(FiscalItem, FiscalNote)
        .join(FiscalNote, FiscalItem.note_id == FiscalNote.id)
        .order_by(FiscalNote.date.desc(), FiscalItem.id.desc())
    )

    # Aplica o limite explicitamente para garantir que o parâmetro seja corretamente bindado
    compiled_stmt = stmt.limit(limit).compile(
        db.bind, compile_kwargs={"oliteral_binds": True}
    )
    logger.info(f"[fiscal-items] Statement generated: {compiled_stmt}")

    result = db.execute(stmt.limit(limit))
    logger.info(f"[fiscal-items] Database execute result type: {type(result)}")
    rows = result.all()
    logger.info(f"[fiscal-items] Rows fetched from database: {len(rows)}")

    items = []
    for fiscal_item, fiscal_note in rows:
        items.append(
            {
                "id": fiscal_item.id,
                "product_name": fiscal_item.product_name,
                "quantity": fiscal_item.quantity,
                "unit_price": fiscal_item.unit_price,
                "total_price": fiscal_item.total_price,
                "category_id": fiscal_item.category_id,
                "product_ean": fiscal_item.product_ean,
                "note_id": fiscal_note.id,
                "note_date": fiscal_note.date.isoformat(),
                "seller_name": fiscal_note.seller_name,
            }
        )

    logger.info(f"[fiscal-items] Quantidade de itens retornados: {len(items)}")

    return items


@app.get("/fiscal-items/orphans")
def list_orphan_fiscal_items(
    db: Session = Depends(get_db),
) -> List[dict]:
    """Lista os itens fiscais que ainda não possuem product_ean (órfãos)."""

    logger.info(
        "[fiscal-items/orphans] Buscando itens fiscais órfãos (sem product_ean)"
    )

    stmt = (
        select(FiscalItem, FiscalNote)
        .join(FiscalNote, FiscalItem.note_id == FiscalNote.id)
        .where(FiscalItem.product_ean.is_(None))
        .order_by(FiscalNote.date.desc(), FiscalItem.id.desc())
    )

    result = db.execute(stmt)
    rows = result.all()

    logger.info(
        f"[fiscal-items/orphans] Quantidade de itens órfãos encontrados: {len(rows)}"
    )

    items = []
    for fiscal_item, fiscal_note in rows:
        items.append(
            {
                "id": fiscal_item.id,
                "product_name": fiscal_item.product_name,
                "quantity": fiscal_item.quantity,
                "unit_price": fiscal_item.unit_price,
                "total_price": fiscal_item.total_price,
                "category_id": fiscal_item.category_id,
                "product_ean": fiscal_item.product_ean,
                "note_id": fiscal_note.id,
                "note_date": fiscal_note.date.isoformat(),
                "seller_name": fiscal_note.seller_name,
            }
        )

    logger.info(f"[fiscal-items/orphans] Itens órfãos retornados: {len(items)}")

    return items


@app.post("/products/eans/")
def create_product_master(
    product: ProductMasterCreate,
    db: Session = Depends(get_db),
) -> dict:
    """Cria ou atualiza um produto master com base no EAN."""

    logger.info(
        f"[products/eans] Criando/atualizando produto master: EAN {product.ean}"
    )

    # Validate that EAN has at least 13 digits
    if len(product.ean) < 13 or not product.ean.isdigit():
        raise HTTPException(
            status_code=400, detail="EAN deve ter pelo menos 13 dígitos numéricos"
        )

    # Convert EAN to integer for storage
    ean_int = int(product.ean)

    # Check if product already exists
    existing_product = (
        db.query(ProductMaster).filter(ProductMaster.ean == ean_int).first()
    )

    if existing_product:
        # Update existing product
        existing_product.name_standard = product.name_standard
        existing_product.category_id = product.category_id
        db.commit()
        db.refresh(existing_product)
        logger.info(f"[products/eans] Produto atualizado: ID {existing_product.id}")
        return {
            "message": "Produto atualizado com sucesso",
            "id": existing_product.id,
            "ean": existing_product.ean,
        }
    else:
        # Create new product
        new_product = ProductMaster(
            ean=ean_int,
            name_standard=product.name_standard,
            category_id=product.category_id,
        )
        db.add(new_product)
        db.commit()
        db.refresh(new_product)
        logger.info(f"[products/eans] Novo produto criado: EAN {new_product.ean}")
        return {"message": "Produto criado com sucesso", "ean": new_product.ean}


@app.post("/product-mappings/")
def create_product_mapping(
    mapping: ProductMappingCreate,
    db: Session = Depends(get_db),
) -> dict:
    """Cria um novo mapeamento entre descrição bruta e produto EAN."""

    logger.info(
        f"[product-mappings] Criando mapeamento: {mapping.raw_description} -> EAN {mapping.product_ean}"
    )

    # Verifica se o EAN existe na tabela products_master
    product = (
        db.query(ProductMaster).filter(ProductMaster.ean == mapping.product_ean).first()
    )
    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Produto com EAN {mapping.product_ean} não encontrado",
        )

    # Verifica se já existe um mapeamento com a mesma descrição e vendedor
    existing_mapping = (
        db.query(ProductMapping)
        .filter(
            ProductMapping.raw_description == mapping.raw_description,
            ProductMapping.seller_name == mapping.seller_name,
        )
        .first()
    )

    if existing_mapping:
        # Atualiza o mapeamento existente
        existing_mapping.product_ean = mapping.product_ean
        db.commit()
        logger.info(
            f"[product-mappings] Mapeamento atualizado: ID {existing_mapping.id}"
        )
        return {
            "message": "Mapeamento atualizado com sucesso",
            "id": existing_mapping.id,
        }
    else:
        # Cria um novo mapeamento
        new_mapping = ProductMapping(
            raw_description=mapping.raw_description,
            seller_name=mapping.seller_name,
            product_ean=mapping.product_ean,
        )
        db.add(new_mapping)
        db.commit()
        db.refresh(new_mapping)
        logger.info(f"[product-mappings] Novo mapeamento criado: ID {new_mapping.id}")
        return {"message": "Mapeamento criado com sucesso", "id": new_mapping.id}


def clean_product_name(product_name: str) -> str:
    """
    Função para limpar nomes de produtos removendo caracteres especiais
    e convertendo para minúsculas para melhor comparação.
    """
    if not product_name:
        return ""
    # Remove caracteres especiais e espaços extras, converte para minúsculas
    cleaned = re.sub(r"[^\w\s]", " ", product_name.lower())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


@app.get("/analytics/price-comparison")
def get_price_comparison(
    product_name: str = Query(
        ..., description="Nome do produto para comparação de preços"
    ),
    db: Session = Depends(get_db),
) -> List[dict]:
    """Endpoint para comparar preços de produtos entre diferentes mercados."""

    # Limpa o nome do produto para busca
    cleaned_product_name = clean_product_name(product_name)

    # Consulta para obter preços de produtos similares por mercado
    stmt = (
        select(
            FiscalItem.product_name,
            FiscalItem.unit_price,
            FiscalNote.date,
            FiscalNote.seller_name,
        )
        .join(FiscalNote, FiscalItem.note_id == FiscalNote.id)
        .where(func.lower(FiscalItem.product_name).contains(cleaned_product_name))
        .order_by(FiscalNote.date.desc())
    )

    result = db.execute(stmt)
    rows = result.all()

    comparison_data = []
    for product_name, unit_price, date, seller_name in rows:
        comparison_data.append(
            {
                "product_name": product_name,
                "unit_price": float(unit_price),
                "date": date.isoformat(),
                "seller_name": seller_name,
            }
        )

    return comparison_data


__all__ = ["app", "get_db", "DATABASE_URL", "SQLITE_DB_PATH"]
