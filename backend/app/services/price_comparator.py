import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models import FiscalItem


@dataclass
class ComparisonResult:
    """Resultado da comparação de preços."""

    is_deal: bool
    base_avg_price: float
    matched_items: List[FiscalItem]
    matched_name: str
    savings_percent: Optional[float] = None


class PriceComparator:
    """Serviço de comparação de preços com base histórica.

    Este serviço recebe ofertas (produto + preço) e compara com os preços
    históricos do sistema para identificar promoções.
    """

    STOP_WORDS = {
        "de",
        "do",
        "da",
        "em",
        "para",
        "com",
        "sem",
        "kg",
        "ml",
        "l",
        "g",
        "un",
        "pc",
        "pct",
    }

    PRIORITY_WORDS = [
        "presunto",
        "cozido",
        "oleo",
        "arroz",
        "feijao",
        "leite",
        "açucar",
        "azeite",
    ]

    def __init__(self, min_match_score: float = 0.3):
        self.min_match_score = min_match_score

    def clean_product_name(self, product_name: str) -> str:
        """Limpa nome do produto para comparação."""
        if not product_name:
            return ""
        cleaned = re.sub(r"[^\w\s]", " ", product_name.lower())
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def find_match(
        self, offer_description: str, db: Session
    ) -> Optional[Tuple[List[FiscalItem], str]]:
        """Encontra o melhor match na base de dados.

        Args:
            offer_description: Descrição da oferta (do flyer ou site)
            db: Sessão do banco de dados

        Returns:
            Tupla (itens_encontrados, nome_matched) ou None se não encontrar
        """
        cleaned_offer = self.clean_product_name(offer_description)
        offer_words = set(cleaned_offer.split())
        offer_keywords = offer_words - self.STOP_WORDS

        if not offer_keywords:
            return None

        all_items = db.query(FiscalItem).all()
        best_match = None
        best_score = 0

        for item in all_items:
            item_cleaned = self.clean_product_name(item.product_name)
            item_words = set(item_cleaned.split()) - self.STOP_WORDS

            intersection = offer_keywords & item_words

            if intersection:
                score = len(intersection) / len(offer_keywords)

                for word in self.PRIORITY_WORDS:
                    if word in item_cleaned and word in cleaned_offer:
                        score += 0.2

                if score > best_score:
                    best_score = score
                    best_match = item

        if best_match and best_score >= self.min_match_score:
            from app.repositories import FiscalItemRepository

            repo = FiscalItemRepository(db)
            items = repo.get_by_product_name(best_match.product_name, 3)
            if items:
                return (items, best_match.product_name)

        return None

    def compare(
        self, offer_description: str, offer_price: float, db: Session
    ) -> Optional[ComparisonResult]:
        """Compara uma oferta com preços históricos.

        Args:
            offer_description: Descrição do produto na oferta
            offer_price: Preço da oferta
            db: Sessão do banco de dados

        Returns:
            ComparisonResult com detalhes da comparação, ou None se não encontrar match
        """
        match_result = self.find_match(offer_description, db)

        if not match_result:
            return None

        items, matched_name = match_result

        prices = [item.unit_price for item in items if item.unit_price]
        if not prices:
            return None

        base_avg_price = sum(prices) / len(prices)
        is_deal = offer_price < base_avg_price

        savings_percent = None
        if is_deal and base_avg_price > 0:
            savings_percent = round(
                ((base_avg_price - offer_price) / base_avg_price) * 100, 2
            )

        return ComparisonResult(
            is_deal=is_deal,
            base_avg_price=round(base_avg_price, 2),
            matched_items=items,
            matched_name=matched_name,
            savings_percent=savings_percent,
        )

    def compare_batch(
        self, offers: List[Tuple[str, float]], db: Session
    ) -> List[ComparisonResult]:
        """Compara múltiplas ofertas de uma vez.

        Args:
            offers: Lista de tuplas (descricao, preco)
            db: Sessão do banco de dados

        Returns:
            Lista de resultados (exclui None/matches não encontrados)
        """
        results = []
        for description, price in offers:
            result = self.compare(description, price, db)
            if result:
                results.append(result)
        return results
