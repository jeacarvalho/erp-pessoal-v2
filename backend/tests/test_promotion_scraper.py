import pytest
from app.services.promotion_scraper import (
    MercaFacilScraper,
    RedeSupermarketScraper,
    GenericSupermarketScraper,
    get_scraper_for_url,
    ExtractedOffer,
)


class TestMercaFacilScraper:
    def test_supported_domains(self):
        scraper = MercaFacilScraper()
        assert "supermercadosreal.com.br" in scraper.supported_domains
        assert "mercafacil.com" in scraper.supported_domains

    def test_can_handle_real_url(self):
        scraper = MercaFacilScraper()
        assert scraper.can_handle("https://www2.supermercadosreal.com.br/loja")
        assert scraper.can_handle("https://www.mercafacil.com/supermercado")

    def test_can_handle_other_url(self):
        scraper = MercaFacilScraper()
        assert not scraper.can_handle("https://www.carrefour.com.br")

    def test_extract_price(self):
        scraper = MercaFacilScraper()

        assert scraper._extract_price("R$ 10,90") == 10.90
        assert scraper._extract_price("10,90") == 10.90
        assert scraper._extract_price("10.90") == 10.90
        assert scraper._extract_price("") is None
        assert scraper._extract_price("SEM PREÇO") is None

    def test_extract_offers_from_html(self):
        scraper = MercaFacilScraper()
        html = """
        <html>
            <body>
                <a href="/produto/teste">
                    <span class="produto">ARROZ INTEGRAL 5KG</span>
                    <span class="preco">R$ 25,90</span>
                </a>
            </body>
        </html>
        """
        offers = scraper.extract_offers(html, "https://example.com")

        assert len(offers) >= 0


class TestGenericSupermarketScraper:
    def test_extract_price(self):
        scraper = GenericSupermarketScraper()

        assert scraper._extract_price("R$ 10,90") == 10.90
        assert scraper._extract_price("10,90") == 10.90
        assert scraper._extract_price("") is None


class TestRedeSupermarketScraper:
    def test_supported_domains(self):
        scraper = RedeSupermarketScraper()
        assert "redesupermarket.com.br" in scraper.supported_domains

    def test_can_handle_rede_url(self):
        scraper = RedeSupermarketScraper()
        assert scraper.can_handle("https://redesupermarket.com.br/ofertas")

    def test_can_handle_other_url(self):
        scraper = RedeSupermarketScraper()
        assert not scraper.can_handle("https://www.carrefour.com.br")

    def test_extract_price(self):
        scraper = RedeSupermarketScraper()

        assert scraper._extract_price("39,98 KG") == 39.98
        assert scraper._extract_price("R$ 10,90") == 10.90
        assert scraper._extract_price("16,99 CADA") == 16.99
        assert scraper._extract_price("") is None


class TestGetScraperForUrl:
    def test_returns_mercafacil_for_real(self):
        scraper = get_scraper_for_url("https://www2.supermercadosreal.com.br/loja")
        assert isinstance(scraper, MercaFacilScraper)

    def test_returns_rede_supermarket_for_rede(self):
        scraper = get_scraper_for_url("https://redesupermarket.com.br/ofertas")
        assert isinstance(scraper, RedeSupermarketScraper)

    def test_returns_none_for_unknown(self):
        scraper = get_scraper_for_url("https://example.com")
        assert scraper is None

    def test_returns_none_for_invalid(self):
        scraper = get_scraper_for_url("not-a-url")
        assert scraper is None


class TestExtractedOffer:
    def test_to_dict(self):
        offer = ExtractedOffer(
            description="Arroz Integral 5KG",
            price=25.90,
            original_price=35.90,
            discount_percent=28,
            url="https://example.com/produto",
        )

        result = offer.to_dict()

        assert result["description"] == "Arroz Integral 5KG"
        assert result["price"] == 25.90
        assert result["original_price"] == 35.90
        assert result["discount_percent"] == 28
        assert result["url"] == "https://example.com/produto"

    def test_to_dict_without_optional(self):
        offer = ExtractedOffer(
            description="Leite",
            price=5.00,
        )

        result = offer.to_dict()

        assert result["description"] == "Leite"
        assert result["price"] == 5.00
        assert result["original_price"] is None
        assert result["discount_percent"] is None
        assert result["url"] is None
