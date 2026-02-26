from __future__ import annotations

from datetime import date
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from .models import (
    BankTransaction,
    Category,
    FiscalItem,
    FiscalNote,
    FiscalSourceType,
    ProductMapping,
    ProductMaster,
)
from .services.xml_handler import ParsedNote


class CategoryRepository:
    def __init__(self, db: Session):
        self._db = db

    def get_all(self) -> List[Category]:
        result = self._db.execute(select(Category).order_by(Category.name))
        return list(result.scalars().all())

    def get_by_id(self, category_id: int) -> Optional[Category]:
        return self._db.get(Category, category_id)

    def get_tree(self) -> List[dict]:
        categories = self.get_all()
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


class TransactionRepository:
    def __init__(self, db: Session):
        self._db = db

    def get_all(self, category_id: Optional[int] = None) -> List[BankTransaction]:
        stmt = select(BankTransaction).order_by(BankTransaction.date.desc())
        if category_id is not None:
            stmt = stmt.where(BankTransaction.category_id == category_id)

        result = self._db.execute(stmt)
        return list(result.scalars().all())

    def create(self, transaction: BankTransaction) -> BankTransaction:
        self._db.add(transaction)
        self._db.commit()
        self._db.refresh(transaction)
        return transaction


class FiscalNoteRepository:
    def __init__(self, db: Session):
        self._db = db

    def get_all(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        seller_name: Optional[str] = None,
    ) -> List[FiscalNote]:
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

        result = self._db.execute(stmt)
        return list(result.unique().scalars().all())

    def get_by_id(self, note_id: int) -> Optional[FiscalNote]:
        return (
            self._db.query(FiscalNote)
            .options(joinedload(FiscalNote.items))
            .filter(FiscalNote.id == note_id)
            .first()
        )

    def create(self, note: FiscalNote) -> FiscalNote:
        self._db.add(note)
        self._db.flush()
        return note

    def commit(self) -> None:
        self._db.commit()

    def refresh(self, note: FiscalNote) -> FiscalNote:
        self._db.refresh(note)
        return note


class FiscalItemRepository:
    def __init__(self, db: Session):
        self._db = db

    def get_all(self, limit: int = 50) -> List[tuple[FiscalItem, FiscalNote]]:
        stmt = (
            select(FiscalItem, FiscalNote)
            .join(FiscalNote, FiscalItem.note_id == FiscalNote.id)
            .order_by(FiscalNote.date.desc(), FiscalItem.id.desc())
        )

        result = self._db.execute(stmt.limit(limit))
        return list(result.all())

    def get_orphans(self) -> List[tuple[FiscalItem, FiscalNote]]:
        stmt = (
            select(FiscalItem, FiscalNote)
            .join(FiscalNote, FiscalItem.note_id == FiscalNote.id)
            .where(FiscalItem.product_ean.is_(None))
            .order_by(FiscalNote.date.desc(), FiscalItem.id.desc())
        )

        result = self._db.execute(stmt)
        return list(result.all())

    def get_by_product_name(
        self, product_name: str, limit: int = 3
    ) -> List[FiscalItem]:
        stmt = (
            select(FiscalItem)
            .join(FiscalNote, FiscalItem.note_id == FiscalNote.id)
            .where(FiscalItem.product_name.ilike(f"%{product_name}%"))
            .order_by(FiscalNote.date.desc())
            .limit(limit)
        )
        return list(self._db.execute(stmt).scalars().all())

    def create(self, item: FiscalItem) -> FiscalItem:
        self._db.add(item)
        return item


class ProductRepository:
    def __init__(self, db: Session):
        self._db = db

    def get_master_by_ean(self, ean: int) -> Optional[ProductMaster]:
        return self._db.query(ProductMaster).filter(ProductMaster.ean == ean).first()

    def create_master(
        self, ean: int, name_standard: str, category_id: Optional[int]
    ) -> ProductMaster:
        product = ProductMaster(
            ean=ean,
            name_standard=name_standard,
            category_id=category_id,
        )
        self._db.add(product)
        self._db.commit()
        self._db.refresh(product)
        return product

    def update_master(
        self, product: ProductMaster, name_standard: str, category_id: Optional[int]
    ) -> ProductMaster:
        product.name_standard = name_standard
        product.category_id = category_id
        self._db.commit()
        self._db.refresh(product)
        return product

    def get_mapping(
        self, raw_description: str, seller_name: str
    ) -> Optional[ProductMapping]:
        return self._db.execute(
            select(ProductMapping).where(
                (ProductMapping.raw_description == raw_description)
                & (ProductMapping.seller_name == seller_name)
            )
        ).scalar_one_or_none()

    def create_mapping(
        self, raw_description: str, seller_name: str, product_ean: int
    ) -> ProductMapping:
        mapping = ProductMapping(
            raw_description=raw_description,
            seller_name=seller_name,
            product_ean=product_ean,
        )
        self._db.add(mapping)
        self._db.commit()
        self._db.refresh(mapping)
        return mapping

    def update_mapping(
        self, mapping: ProductMapping, product_ean: int
    ) -> ProductMapping:
        mapping.product_ean = product_ean
        self._db.commit()
        self._db.refresh(mapping)
        return mapping


class FiscalNoteService:
    def __init__(self, db: Session):
        self._db = db
        self._note_repo = FiscalNoteRepository(db)
        self._item_repo = FiscalItemRepository(db)
        self._product_repo = ProductRepository(db)

    def persist_parsed_note(
        self, parsed: ParsedNote, source_type: FiscalSourceType
    ) -> FiscalNote:
        note = FiscalNote(
            date=parsed.date,
            total_amount=parsed.total_amount,
            seller_name=parsed.seller_name,
            access_key=parsed.access_key,
            source_type=source_type,
        )

        self._note_repo.create(note)

        try:
            self._db.flush()
        except Exception:
            self._db.rollback()
            raise

        for item in parsed.items:
            mapping = self._product_repo.get_mapping(item.name, parsed.seller_name)

            product_ean = item.ean
            if product_ean is None and mapping:
                product_ean = mapping.product_ean

            fiscal_item = FiscalItem(
                note_id=note.id,
                product_name=item.name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price,
                category_id=None,
                product_ean=product_ean,
            )
            self._item_repo.create(fiscal_item)

        self._note_repo.commit()
        self._note_repo.refresh(note)
        return note
