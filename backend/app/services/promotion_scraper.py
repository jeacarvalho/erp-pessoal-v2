import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

import requests
from bs4 import BeautifulSoup


@dataclass
class ExtractedOffer:
    """Representa uma oferta extraída de um site de supermercado."""

    description: str
    price: float
    original_price: Optional[float] = None
    discount_percent: Optional[int] = None
    url: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "price": self.price,
            "original_price": self.original_price,
            "discount_percent": self.discount_percent,
            "url": self.url,
        }


class BasePromotionScraper(ABC):
    """Classe base para scrapers de promoções de supermercados.

    Cada supermercado pode ter uma estrutura de HTML diferente.
    Esta classe define a interface que implementações devem seguir.
    """

    @property
    @abstractmethod
    def supported_domains(self) -> List[str]:
        """Lista de domínios suportados por este scraper."""
        pass

    @abstractmethod
    def extract_offers(self, html: str, url: str) -> List[ExtractedOffer]:
        """Extrai ofertas (produto + preço) do HTML da página.

        Args:
            html: Conteúdo HTML da página
            url: URL original (para construir links de produtos)

        Returns:
            Lista de ofertas extraídas
        """
        pass

    def can_handle(self, url: str) -> bool:
        """Verifica se este scraper pode processar a URL."""
        return any(domain in url for domain in self.supported_domains)

    def fetch(self, url: str) -> List[ExtractedOffer]:
        """Faz o fetch da URL e extrai as ofertas.

        Args:
            url: URL da página de promoções

        Returns:
            Lista de ofertas extraídas
        """
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        return self.extract_offers(response.text, url)


class GenericSupermarketScraper(BasePromotionScraper):
    """Scraper genérico para sites de supermercado que seguem padrão comum.

    Este scraper tenta detectar:
    - Nome do produto
    - Preço atual
    - Preço original (se houver desconto)
    - Percentual de desconto
    """

    @property
    def supported_domains(self) -> List[str]:
        return []

    def extract_offers(self, html: str, url: str) -> List[ExtractedOffer]:
        soup = BeautifulSoup(html, "html.parser")
        offers = []

        for product_card in soup.select(
            "[class*='product'], [class*=' Produto'], .product-card, .product-item, [data-product]"
        ):
            name_elem = product_card.select_one(
                "[class*='name'], [class*='title'], h3, h4, .product-name, .nome"
            )
            price_elem = product_card.select_one(
                "[class*='price'], .valor, .preco, [class*='promo']"
            )

            if not name_elem or not price_elem:
                continue

            name = name_elem.get_text(strip=True)
            price_text = price_elem.get_text(strip=True)

            price = self._extract_price(price_text)
            if not price:
                continue

            original_price = None
            discount_percent = None

            old_price_elem = product_card.select_one(
                "[class*='old'], [class*='de'], .preco-antigo, .original-price"
            )
            if old_price_elem:
                original_price = self._extract_price(old_price_elem.get_text())
                if original_price and original_price > price:
                    discount_percent = int(
                        ((original_price - price) / original_price) * 100
                    )

            offers.append(
                ExtractedOffer(
                    description=name,
                    price=price,
                    original_price=original_price,
                    discount_percent=discount_percent,
                )
            )

        return offers

    def _extract_price(self, text: str) -> Optional[float]:
        """Extrai preço de uma string."""
        text = text.replace("R$", "").replace("$", "").strip()
        text = re.sub(r"[^\d,]", "", text)
        text = text.replace(",", ".")

        try:
            return float(text)
        except (ValueError, AttributeError):
            return None


class MercaFacilScraper(BasePromotionScraper):
    """Scraper específico para sites que usam a plataforma MercaFácil.

    O Supermercados Real usa esta plataforma.
    """

    @property
    def supported_domains(self) -> List[str]:
        return [
            "supermercadosreal.com.br",
            "mercafacil.com",
        ]

    def extract_offers(self, html: str, url: str) -> List[ExtractedOffer]:
        soup = BeautifulSoup(html, "html.parser")
        offers = []

        for product_card in soup.select("a[href*='/produto/']"):
            name_elem = product_card.select_one(
                "[class*='produto'], .product-name, h3, h4"
            )
            price_elem = product_card.select_one(
                "[class*='preco'], [class*='price'], .valor, .promo"
            )

            if not name_elem or not price_elem:
                continue

            name = name_elem.get_text(strip=True)
            price_text = price_elem.get_text(strip=True)

            price = self._extract_price(price_text)
            if not price:
                continue

            original_price = None
            discount_percent = None

            old_price_elem = product_card.select_one("[class*='antigo'], [class*='de']")
            if old_price_elem:
                original_price = self._extract_price(old_price_elem.get_text())
                if original_price and original_price > price:
                    discount_percent = int(
                        ((original_price - price) / original_price) * 100
                    )

            link = product_card.get("href", "")
            if link and not link.startswith("http"):
                link = "https://www2.supermercadosreal.com.br" + link

            offers.append(
                ExtractedOffer(
                    description=name,
                    price=price,
                    original_price=original_price,
                    discount_percent=discount_percent,
                    url=link if link else None,
                )
            )

        return offers

    def _extract_price(self, text: str) -> Optional[float]:
        """Extrai preço de uma string."""
        text = text.replace("R$", "").replace("$", "").strip()

        match = re.search(r"[\d]+[.,]?\d*", text)
        if match:
            try:
                return float(match.group().replace(",", "."))
            except ValueError:
                return None
        return None


class RedeSupermarketScraper(BasePromotionScraper):
    """Scraper específico para o site Rede Supermarket.

    Site WordPress com ofertas em formato simples de texto.
    """

    @property
    def supported_domains(self) -> List[str]:
        return ["redesupermarket.com.br"]

    def extract_offers(self, html: str, url: str) -> List[ExtractedOffer]:
        soup = BeautifulSoup(html, "html.parser")
        offers = []

        for product_card in soup.select(".col-6, .product-card, .offer-item, article"):
            name_elem = product_card.select_one(
                "h3, h4, .product-name, .title, [class*='title']"
            )
            price_elem = product_card.select_one("[class*='price'], .valor, .preco")

            if not name_elem:
                continue

            name = name_elem.get_text(strip=True)
            if not name or len(name) < 3:
                continue

            price = None
            if price_elem:
                price = self._extract_price(price_elem.get_text())

            if not price:
                text = product_card.get_text()
                price = self._extract_price(text)

            if price:
                offers.append(
                    ExtractedOffer(
                        description=name,
                        price=price,
                    )
                )

        if not offers:
            for h3 in soup.select("h3"):
                text = h3.get_text(strip=True)
                parent = h3.parent
                if parent:
                    parent_text = parent.get_text()
                    price = self._extract_price(parent_text)
                    if price and text:
                        offers.append(
                            ExtractedOffer(
                                description=text,
                                price=price,
                            )
                        )

        return offers

    def _extract_price(self, text: str) -> Optional[float]:
        """Extrai preço de uma string."""
        text = text.replace("R$", "").replace("$", "").strip()

        patterns = [
            r"(\d+[\.,]\d{2})\s*(?:KG|CADA|UN|L)?",
            r"(\d+[\.,]\d{2})$",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1).replace(",", "."))
                except ValueError:
                    continue

        return None


def get_scraper_for_url(url: str) -> Optional[BasePromotionScraper]:
    """Retorna o scraper adequado para a URL.

    Args:
        url: URL do site de promoções

    Returns:
        Scraper apropriado ou None se não encontrado
    """
    scrapers = [
        MercaFacilScraper(),
        RedeSupermarketScraper(),
        GenericSupermarketScraper(),
    ]

    for scraper in scrapers:
        if scraper.can_handle(url):
            return scraper

    return None
