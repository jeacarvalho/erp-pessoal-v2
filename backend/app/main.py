from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import List, Optional
from urllib.parse import unquote

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import engine, SessionLocal, get_db
from app.models import (
    BankTransaction,
    Category,
    FiscalItem,
    FiscalNote,
    FiscalSourceType,
    ProductMapping,
    Base,
)
from app.repositories import (
    CategoryRepository,
    FiscalItemRepository,
    FiscalNoteRepository,
    FiscalNoteService,
    ProductRepository,
    TransactionRepository,
)
from app.schemas import (
    CategoryOut,
    FiscalItemOut,
    FiscalNoteOut,
    ProductMappingCreate,
    ProductMasterCreate,
    SellerTrendProduct,
    SellerTrendsOut,
    TransactionCreate,
    TransactionOut,
)
from app.seed import seed_categories
from app.services.flyer_analyzer import FlyerAnalyzer
from app.services.price_comparator import PriceComparator
from app.services.promotion_scraper import get_scraper_for_url
from app.services.scraper_handler import ScraperImporter
from app.services.xml_handler import XMLProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL: str = (
    os.getenv("DATABASE_URL")
    or f"sqlite+pysqlite:///{os.getenv('SQLITE_DB_PATH', '../data/sqlite/app.db')}"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[lifespan] DATABASE_URL = {DATABASE_URL}")
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

    yield
    print("[lifespan] Encerrando aplicação...")


app = FastAPI(title="ERP Pessoal API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Backend is running"}


@app.get("/categories", response_model=List[CategoryOut])
def list_categories(db: Session = Depends(get_db)) -> List[CategoryOut]:
    repo = CategoryRepository(db)
    categories = repo.get_all()
    return [CategoryOut.model_validate(cat) for cat in categories]


@app.get("/categories/tree")
def list_categories_tree(db: Session = Depends(get_db)) -> List[dict]:
    repo = CategoryRepository(db)
    return repo.get_tree()


@app.post(
    "/transactions", response_model=TransactionOut, status_code=status.HTTP_201_CREATED
)
def create_transaction(
    payload: TransactionCreate, db: Session = Depends(get_db)
) -> TransactionOut:
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
    repo = TransactionRepository(db)
    transaction = repo.create(transaction)
    return TransactionOut.model_validate(transaction)


@app.get("/transactions", response_model=List[TransactionOut])
def list_transactions(
    category_id: Optional[int] = Query(
        default=None, description="Filtra transações por category_id."
    ),
    db: Session = Depends(get_db),
) -> List[TransactionOut]:
    repo = TransactionRepository(db)
    transactions = repo.get_all(category_id)
    return [TransactionOut.model_validate(tx) for tx in transactions]


@app.get("/fiscal-notes", response_model=List[FiscalNoteOut])
def list_fiscal_notes(
    date_from: Optional[date] = Query(
        default=None, description="Data inicial (ISO YYYY-MM-DD)."
    ),
    date_to: Optional[date] = Query(
        default=None, description="Data final (ISO YYYY-MM-DD)."
    ),
    seller_name: Optional[str] = Query(
        default=None, description="Filtrar por nome do estabelecimento."
    ),
    db: Session = Depends(get_db),
) -> List[FiscalNoteOut]:
    repo = FiscalNoteRepository(db)
    notes = repo.get_all(date_from, date_to, seller_name)
    return [FiscalNoteOut.model_validate(note) for note in notes]


@app.get("/fiscal-notes/{note_id}", response_model=FiscalNoteOut)
def get_fiscal_note(note_id: int, db: Session = Depends(get_db)) -> FiscalNoteOut:
    repo = FiscalNoteRepository(db)
    note = repo.get_by_id(note_id)
    if note is None:
        raise HTTPException(
            status_code=404, detail=f"Nota fiscal com ID {note_id} não encontrada."
        )
    return FiscalNoteOut.model_validate(note)


class FiscalNoteCreate(BaseModel):
    number: str
    serie: str
    cnpj: str
    emission_date: datetime
    total_value: float
    seller_name: Optional[str] = None
    access_key: Optional[str] = None


@app.post("/fiscal-notes", response_model=FiscalNoteOut)
def create_fiscal_note(
    note_data: FiscalNoteCreate, db: Session = Depends(get_db)
) -> FiscalNoteOut:
    note = FiscalNote(
        date=note_data.emission_date.date(),
        total_amount=note_data.total_value,
        seller_name=note_data.seller_name or "Unknown Seller",
        access_key=note_data.access_key or f"KEY_{note_data.number}",
        source_type=FiscalSourceType.SCRAPING,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return FiscalNoteOut.model_validate(note)


class FiscalItemCreate(BaseModel):
    description: str
    quantity: float
    unit_value: float
    total_value: float
    product_ean: Optional[str] = None


@app.post("/fiscal-notes/{note_id}/items", response_model=FiscalItemOut)
def create_fiscal_item(
    note_id: int, item_data: FiscalItemCreate, db: Session = Depends(get_db)
) -> FiscalItemOut:
    note = db.query(FiscalNote).filter(FiscalNote.id == note_id).first()
    if not note:
        raise HTTPException(
            status_code=404, detail=f"Nota fiscal com ID {note_id} não encontrada."
        )

    product_mapping = db.execute(
        select(ProductMapping).where(
            (ProductMapping.raw_description == item_data.description)
            & (ProductMapping.seller_name == note.seller_name)
        )
    ).scalar_one_or_none()

    product_ean = item_data.product_ean
    if not product_ean and product_mapping:
        product_ean = str(product_mapping.product_ean)

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
    return FiscalItemOut.model_validate(fiscal_item)


@app.get("/fiscal-items")
def list_fiscal_items(
    limit: int = Query(default=50, ge=1, le=500), db: Session = Depends(get_db)
) -> List[dict]:
    repo = FiscalItemRepository(db)
    rows = repo.get_all(limit)
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
    return items


@app.get("/fiscal-items/orphans")
def list_orphan_fiscal_items(db: Session = Depends(get_db)) -> List[dict]:
    repo = FiscalItemRepository(db)
    rows = repo.get_orphans()
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
    return items


@app.post("/products/eans/")
def create_product_master(
    product: ProductMasterCreate, db: Session = Depends(get_db)
) -> dict:
    if len(product.ean) < 13 or not product.ean.isdigit():
        raise HTTPException(
            status_code=400, detail="EAN deve ter pelo menos 13 dígitos numéricos"
        )

    ean_int = int(product.ean)
    repo = ProductRepository(db)
    existing = repo.get_master_by_ean(ean_int)

    if existing:
        repo.update_master(existing, product.name_standard, product.category_id)
        return {"message": "Produto atualizado com sucesso", "ean": existing.ean}
    else:
        new_product = repo.create_master(
            ean_int, product.name_standard, product.category_id
        )
        return {"message": "Produto criado com sucesso", "ean": new_product.ean}


@app.post("/product-mappings/")
def create_product_mapping(
    mapping: ProductMappingCreate, db: Session = Depends(get_db)
) -> dict:
    repo = ProductRepository(db)
    product = repo.get_master_by_ean(mapping.product_ean)
    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Produto com EAN {mapping.product_ean} não encontrado",
        )

    existing = db.execute(
        select(ProductMapping).where(
            ProductMapping.raw_description == mapping.raw_description,
            ProductMapping.seller_name == mapping.seller_name,
        )
    ).scalar_one_or_none()

    if existing:
        repo.update_mapping(existing, mapping.product_ean)
        return {"message": "Mapeamento atualizado com sucesso", "id": existing.id}
    else:
        new_mapping = repo.create_mapping(
            mapping.raw_description, mapping.seller_name, mapping.product_ean
        )
        return {"message": "Mapeamento criado com sucesso", "id": new_mapping.id}


@app.get("/analytics/price-comparison")
def get_price_comparison(
    product_name: str = Query(...), db: Session = Depends(get_db)
) -> List[dict]:
    comparator = PriceComparator()
    cleaned_product_name = comparator.clean_product_name(product_name)
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
    for prod_name, unit_price, transaction_date, seller_name in rows:
        comparison_data.append(
            {
                "product_name": prod_name,
                "unit_price": float(unit_price),
                "date": transaction_date.isoformat(),
                "seller_name": seller_name,
            }
        )
    return comparison_data


@app.get("/analytics/sellers", response_model=List[str])
def get_sellers(db: Session = Depends(get_db)) -> List[str]:
    sellers = (
        db.query(FiscalNote.seller_name)
        .distinct()
        .order_by(FiscalNote.seller_name)
        .all()
    )
    return [s[0] for s in sellers]


@app.get("/analytics/sellers/with-history", response_model=List[str])
def get_sellers_with_history(db: Session = Depends(get_db)) -> List[str]:
    sellers = (
        db.query(FiscalNote.seller_name, func.count(FiscalNote.id).label("count"))
        .group_by(FiscalNote.seller_name)
        .having(func.count(FiscalNote.id) > 1)
        .order_by(FiscalNote.seller_name)
        .all()
    )
    return [s[0] for s in sellers]


@app.get("/analytics/seller-trends", response_model=SellerTrendsOut)
def get_seller_trends(
    seller_name: str = Query(...), db: Session = Depends(get_db)
) -> dict:
    decoded_name = unquote(seller_name)
    notes = (
        db.query(FiscalNote)
        .filter(FiscalNote.seller_name.ilike(f"%{decoded_name}%"))
        .order_by(FiscalNote.date.desc())
        .limit(3)
        .all()
    )

    if not notes:
        return {"seller_name": decoded_name, "products": []}

    actual_seller_name = notes[0].seller_name
    product_history = {}

    for note in notes:
        for item in note.items:
            product_key = (
                str(item.product_ean) if item.product_ean else item.product_name
            )
            if product_key not in product_history:
                product_history[product_key] = {
                    "product_name": item.product_name,
                    "prices": [],
                }
            product_history[product_key]["prices"].append(item.unit_price)

    products = []
    for product_key, data in product_history.items():
        prices = data["prices"][:3]
        variation_percent = None
        if len(prices) >= 2 and prices[1] > 0:
            variation_percent = round(((prices[0] - prices[1]) / prices[1]) * 100, 2)
        products.append(
            SellerTrendProduct(
                product_key=product_key,
                product_name=data["product_name"],
                price_history=prices,
                variation_percent=variation_percent,
            )
        )

    return {"seller_name": actual_seller_name, "products": products}


class FlyerAnalysisResult(BaseModel):
    product_name: str
    offer_price: float
    base_avg_price: float
    is_deal: bool


@app.post("/analytics/analyze-flyer", response_model=List[FlyerAnalysisResult])
async def analyze_flyer(
    file: UploadFile = File(...), db: Session = Depends(get_db)
) -> List[FlyerAnalysisResult]:
    image_bytes = await file.read()
    analyzer = FlyerAnalyzer()
    offers = analyzer.extract_offers(image_bytes)

    comparator = PriceComparator()
    results = []

    for offer in offers:
        comparison = comparator.compare(offer.description, offer.price, db)
        if comparison:
            results.append(
                FlyerAnalysisResult(
                    product_name=offer.description,
                    offer_price=offer.price,
                    base_avg_price=comparison.base_avg_price,
                    is_deal=comparison.is_deal,
                )
            )

    return results


class ImportUrlPayload(BaseModel):
    url: HttpUrl
    use_browser: bool = False


@app.post("/import/xml")
async def import_xml(
    file: UploadFile = File(...), db: Session = Depends(get_db)
) -> dict:
    content = await file.read()
    processor = XMLProcessor()
    parsed = processor.parse(content)
    service = FiscalNoteService(db)
    note = service.persist_parsed_note(parsed, FiscalSourceType.XML)
    return {
        "note_id": note.id,
        "items_count": len(parsed.items),
        "seller_name": note.seller_name,
        "total_amount": note.total_amount,
    }


@app.post("/import/xml-rj")
async def import_xml_rj(
    file: UploadFile = File(...), db: Session = Depends(get_db)
) -> dict:
    content = await file.read()
    processor = XMLProcessor()
    parsed = processor.parse(content)
    service = FiscalNoteService(db)
    note = service.persist_parsed_note(parsed, FiscalSourceType.XML)
    return {
        "note_id": note.id,
        "items_count": len(parsed.items),
        "seller_name": note.seller_name,
        "total_amount": note.total_amount,
    }


@app.post("/import/url")
def import_url(payload: ImportUrlPayload, db: Session = Depends(get_db)) -> dict:
    importer = ScraperImporter()
    try:
        parsed = importer.import_from_url(
            str(payload.url), force_browser=payload.use_browser
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    service = FiscalNoteService(db)
    note = service.persist_parsed_note(parsed, FiscalSourceType.SCRAPING)
    return {
        "note_id": note.id,
        "items_count": len(parsed.items),
        "seller_name": note.seller_name,
        "total_amount": note.total_amount,
    }


@app.post("/import/restore-from-backup")
def restore_from_backup(db: Session = Depends(get_db)) -> dict:
    import json

    backup_file_path = "../data/processed_urls_backup.json"

    if not os.path.exists(backup_file_path):
        raise HTTPException(
            status_code=404, detail="Arquivo de backup de URLs não encontrado."
        )

    try:
        with open(backup_file_path, "r", encoding="utf-8") as f:
            urls = json.load(f)
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Erro ao ler o arquivo de backup: {str(e)}"
        )

    if not urls:
        return {
            "message": "Nenhuma URL encontrada no arquivo de backup.",
            "total_urls": 0,
            "restored_count": 0,
        }

    restored_count = 0
    errors = []
    importer = ScraperImporter()

    for url in urls:
        try:
            parsed = importer.import_from_url(str(url), force_browser=False)
            import time

            time.sleep(5)
            service = FiscalNoteService(db)
            service.persist_parsed_note(parsed, FiscalSourceType.SCRAPING)
            restored_count += 1
        except Exception as e:
            errors.append({"url": url, "error": str(e)})

    return {
        "message": f"Processo de restauração concluído. {restored_count} de {len(urls)} URLs restauradas.",
        "total_urls": len(urls),
        "restored_count": restored_count,
        "errors": errors,
    }


class UrlAnalysisResult(BaseModel):
    product_name: str
    offer_price: float
    base_avg_price: float
    is_deal: bool
    discount_percent: Optional[int] = None
    original_price: Optional[float] = None
    url: Optional[str] = None


@app.post("/analytics/analyze-url", response_model=List[UrlAnalysisResult])
async def analyze_url(
    url: str = Query(..., description="URL da página de promoções do supermercado"),
    use_browser: bool = Query(False, description="Usar browser para renderizar JS"),
    db: Session = Depends(get_db),
) -> List[UrlAnalysisResult]:
    """Analisa uma URL de promoções de supermercado e compara com preços históricos."""

    scraper = get_scraper_for_url(url)
    if not scraper:
        raise HTTPException(
            status_code=400,
            detail="URL não suportada. Forneça uma URL de supermercado válida.",
        )

    if use_browser:
        from app.services.browser_fetcher import BrowserHTMLFetcher

        fetcher = BrowserHTMLFetcher()
        html = fetcher.fetch(url)
    else:
        import requests

        response = requests.get(url, timeout=30)
        response.raise_for_status()
        html = response.text

    offers = scraper.extract_offers(html, url)

    comparator = PriceComparator()
    results = []

    for offer in offers:
        comparison = comparator.compare(offer.description, offer.price, db)
        if comparison:
            results.append(
                UrlAnalysisResult(
                    product_name=offer.description,
                    offer_price=offer.price,
                    base_avg_price=comparison.base_avg_price,
                    is_deal=comparison.is_deal,
                    discount_percent=offer.discount_percent,
                    original_price=offer.original_price,
                    url=offer.url,
                )
            )

    return results


__all__ = ["app", "get_db", "DATABASE_URL", "SessionLocal"]
