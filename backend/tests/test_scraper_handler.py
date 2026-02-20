"""Tests for scraper_handler module."""

from datetime import date
import pytest
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup

from backend.app.services.scraper_handler import (
    _looks_like_sefaz_block_page,
    BaseSefazAdapter,
    DefaultSefazAdapter,
    RJSefazNFCeAdapter,
    ScraperImporter,
)
from backend.app.services.xml_handler import ParsedItem, ParsedNote


# Helper to add items table to HTML
ITEMS_TABLE = """
<table>
    <tr><th>Produto</th><th>Qtd</th><th>Un</th></tr>
    <tr><td>Item Teste</td><td>1</td><td>UN</td></tr>
</table>
"""


class TestLooksLikeSefazBlockPage:
    """Tests for _looks_like_sefaz_block_page function."""

    def test_detects_blocked_access_portal(self):
        """Should detect 'acesso negado ao portal' text."""
        html = "<html><body>Acesso negado ao portal da SEFAZ</body></html>"
        assert _looks_like_sefaz_block_page(html) is True

    def test_detects_blocked_access(self):
        """Should detect 'acesso bloqueado' text."""
        html = "<html><body>Acesso bloqueado temporariamente</body></html>"
        assert _looks_like_sefaz_block_page(html) is True

    def test_returns_false_for_normal_page(self):
        """Should return False for normal NFC-e page."""
        html = "<html><body>Nota Fiscal Eletrônica</body></html>"
        assert _looks_like_sefaz_block_page(html) is False

    def test_returns_false_for_empty_html(self):
        """Should return False for empty HTML."""
        assert _looks_like_sefaz_block_page("") is False


class TestBaseSefazAdapter:
    """Tests for BaseSefazAdapter class."""

    def test_parse_raises_not_implemented(self):
        """Should raise NotImplementedError."""
        adapter = BaseSefazAdapter()
        with pytest.raises(NotImplementedError):
            adapter.parse("<html></html>")


class TestDefaultSefazAdapter:
    """Tests for DefaultSefazAdapter class."""

    def test_parse_raises_error_on_blocked_page(self):
        """Should raise ValueError on blocked page."""
        adapter = DefaultSefazAdapter()
        html = "<html><body>Acesso negado ao portal</body></html>"

        with pytest.raises(ValueError, match="Acesso à página da NFC-e foi negado"):
            adapter.parse(html)

    def test_parse_extracts_seller_name_with_cnpj(self):
        """Should extract seller name with CNPJ."""
        adapter = DefaultSefazAdapter()
        html = f"""
        <html>
            <div class="txtTopo" id="u20">Supermercado Teste</div>
            <div class="text">CNPJ: 12.345.678/0001-90</div>
            {ITEMS_TABLE}
        </html>
        """

        result = adapter.parse(html)
        assert "Supermercado Teste" in result.seller_name
        assert "CNPJ" in result.seller_name

    def test_parse_extracts_seller_name_from_h1(self):
        """Should extract seller name from h1 tag."""
        adapter = DefaultSefazAdapter()
        html = f"<html><h1>Loja Teste</h1>{ITEMS_TABLE}</html>"

        result = adapter.parse(html)
        assert result.seller_name == "Loja Teste"

    def test_parse_extracts_seller_name_from_h2(self):
        """Should extract seller name from h2 tag."""
        adapter = DefaultSefazAdapter()
        html = f"<html><h2>Mercado Exemplo</h2>{ITEMS_TABLE}</html>"

        result = adapter.parse(html)
        assert result.seller_name == "Mercado Exemplo"

    def test_parse_returns_unknown_seller_when_not_found(self):
        """Should return unknown seller when not found."""
        adapter = DefaultSefazAdapter()
        html = f"<html><body>No seller info</body>{ITEMS_TABLE}</html>"

        result = adapter.parse(html)
        assert result.seller_name == "Estabelecimento Desconhecido"

    def test_extract_access_key_from_span_chave(self):
        """Should extract access key from span with class chave."""
        adapter = DefaultSefazAdapter()
        html = f"""<html><span class="chave">3326 0210 6976 9700 0660 6510 7000 3680 6612 6649 4182</span>{ITEMS_TABLE}</html>"""

        result = adapter.parse(html)
        assert "3326" in result.access_key
        assert len(result.access_key.replace(" ", "")) == 44

    def test_extract_access_key_from_text_pattern(self):
        """Should extract access key from text pattern."""
        adapter = DefaultSefazAdapter()
        html = f"""<html><body>Chave de Acesso: 33260210697697000660651070003680661266494182</body>{ITEMS_TABLE}</html>"""

        result = adapter.parse(html)
        assert "3326" in result.access_key

    def test_extract_access_key_generates_fallback(self):
        """Should generate fallback key when not found."""
        adapter = DefaultSefazAdapter()
        html = f"<html><body>No access key here</body>{ITEMS_TABLE}</html>"

        result = adapter.parse(html)
        assert result.access_key.startswith("SCRAPING-")

    def test_extract_date_from_emission_text(self):
        """Should extract date from emission text."""
        adapter = DefaultSefazAdapter()
        html = f"<html><body>Número: 123 Série: 1 Emissão: 15/03/2024</body>{ITEMS_TABLE}</html>"

        result = adapter.parse(html)
        assert result.date == date(2024, 3, 15)

    def test_extract_date_from_simple_pattern(self):
        """Should extract date from simple DD/MM/YYYY pattern."""
        adapter = DefaultSefazAdapter()
        html = f"<html><body>Data: 20/12/2023</body>{ITEMS_TABLE}</html>"

        result = adapter.parse(html)
        assert result.date == date(2023, 12, 20)

    def test_extract_date_returns_today_when_not_found(self):
        """Should return today's date when not found."""
        adapter = DefaultSefazAdapter()
        html = f"<html><body>No date here</body>{ITEMS_TABLE}</html>"

        result = adapter.parse(html)
        assert result.date == date.today()

    def test_extract_total_amount_from_text(self):
        """Should extract total amount from text."""
        adapter = DefaultSefazAdapter()
        html = f"<html><body>Total da compra: R$ 150,75</body>{ITEMS_TABLE}</html>"

        result = adapter.parse(html)
        assert result.total_amount == 150.75

    def test_extract_items_from_tabresult_table(self):
        """Should extract items from tabResult table."""
        adapter = DefaultSefazAdapter()
        html = """
        <html>
            <table id="tabResult">
                <tr id="Item + 1">
                    <td>
                        <span class="txtTit">Produto Teste</span>
                        <span class="Rqtd">Qtde.: 2</span>
                        <span class="RUN">UN: UN</span>
                        <span class="RvlUnit">Vl. Unit.: 10,50</span>
                    </td>
                    <td><span class="valor">21,00</span></td>
                </tr>
            </table>
        </html>
        """

        result = adapter.parse(html)
        assert len(result.items) == 1
        assert result.items[0].name == "Produto Teste"
        assert result.items[0].quantity == 2.0
        assert result.items[0].unit == "UN"
        assert result.items[0].unit_price == 10.50
        assert result.items[0].total_price == 21.00

    def test_extract_items_from_generic_table(self):
        """Should extract items from generic table."""
        adapter = DefaultSefazAdapter()
        html = """
        <html>
            <table>
                <tr><th>Produto</th><th>Qtd</th><th>Un</th><th>Preço</th><th>Total</th></tr>
                <tr><td>Item 1</td><td>1</td><td>UN</td><td>5,00</td><td>5,00</td></tr>
                <tr><td>Item 2</td><td>3</td><td>KG</td><td>2,00</td><td>6,00</td></tr>
            </table>
        </html>
        """

        result = adapter.parse(html)
        assert len(result.items) == 2
        assert result.items[0].name == "Item 1"
        assert result.items[1].name == "Item 2"

    def test_extract_items_skips_niteroi(self):
        """Should skip items with name 'niteroi'."""
        adapter = DefaultSefazAdapter()
        html = """
        <html>
            <table>
                <tr><th>Produto</th><th>Qtd</th><th>Un</th></tr>
                <tr><td>Niteroi</td><td>1</td><td>UN</td></tr>
                <tr><td>Produto Real</td><td>2</td><td>UN</td></tr>
            </table>
        </html>
        """

        result = adapter.parse(html)
        assert len(result.items) == 1
        assert result.items[0].name == "Produto Real"

    def test_extract_items_raises_error_when_no_items(self):
        """Should raise ValueError when no items found."""
        adapter = DefaultSefazAdapter()
        html = "<html><body>No items here</body></html>"

        with pytest.raises(ValueError, match="Não foi possível localizar itens"):
            adapter.parse(html)


class TestRJSefazNFCeAdapter:
    """Tests for RJSefazNFCeAdapter class."""

    def test_parse_extracts_seller_name_with_cnpj(self):
        """Should extract seller name with CNPJ."""
        adapter = RJSefazNFCeAdapter()
        html = f"""
        <html>
            <div class="txtTopo" id="u20">Supermercado RJ</div>
            <div class="text">CNPJ: 98.765.432/0001-10</div>
            {ITEMS_TABLE}
        </html>
        """

        result = adapter.parse(html)
        assert "Supermercado RJ" in result.seller_name
        assert "CNPJ" in result.seller_name

    def test_parse_extracts_seller_name_from_cnpj_text(self):
        """Should extract seller name from elements containing CNPJ text."""
        adapter = RJSefazNFCeAdapter()
        html = f"""<html><strong>Mercado Exemplo CNPJ: 11.111.111/0001-11</strong>{ITEMS_TABLE}</html>"""

        result = adapter.parse(html)
        assert "Mercado Exemplo" in result.seller_name

    def test_extract_total_amount_from_valor_pagar(self):
        """Should extract total amount from 'Valor a pagar' text."""
        adapter = RJSefazNFCeAdapter()
        html = f"""<html><body>Valor a pagar R$: 89,90</body>{ITEMS_TABLE}</html>"""

        result = adapter.parse(html)
        assert result.total_amount == 89.90

    def test_extract_date_from_emission_pattern(self):
        """Should extract date from emission pattern."""
        adapter = RJSefazNFCeAdapter()
        html = f"""<html><body>Número: 001 Série: 002 Emissão: 25/12/2023</body>{ITEMS_TABLE}</html>"""

        result = adapter.parse(html)
        assert result.date == date(2023, 12, 25)

    def test_extract_access_key_generates_rj_fallback(self):
        """Should generate RJ-specific fallback key."""
        adapter = RJSefazNFCeAdapter()
        html = f"""<html><body>No key</body>{ITEMS_TABLE}</html>"""

        result = adapter.parse(html)
        assert result.access_key.startswith("SCRAPING-RJ-")


class TestScraperImporter:
    """Tests for ScraperImporter class."""

    def test_init_creates_adapters_dict(self):
        """Should initialize adapters dictionary."""
        importer = ScraperImporter()
        assert "default" in importer._adapters
        assert "rj_nfe_moderno" in importer._adapters

    def test_init_creates_backup_directory(self):
        """Should create backup directory."""
        with patch("os.makedirs") as mock_makedirs:
            importer = ScraperImporter("/tmp/test_backup/processed_urls.json")
            mock_makedirs.assert_called_once_with("/tmp/test_backup", exist_ok=True)

    def test_load_processed_urls_from_backup(self):
        """Should load processed URLs from backup file."""
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", MagicMock()) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = (
                    '["http://example.com/1", "http://example.com/2"]'
                )
                with patch(
                    "json.load",
                    return_value=["http://example.com/1", "http://example.com/2"],
                ):
                    importer = ScraperImporter()
                    assert "http://example.com/1" in importer._processed_urls
                    assert "http://example.com/2" in importer._processed_urls

    def test_load_processed_urls_empty_when_file_not_exists(self):
        """Should have empty set when backup file doesn't exist."""
        with patch("os.path.exists", return_value=False):
            importer = ScraperImporter("/tmp/nonexistent/path.json")
            assert importer._processed_urls == set()

    def test_load_processed_urls_empty_on_error(self):
        """Should have empty set when error reading backup."""
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", side_effect=Exception("Read error")):
                importer = ScraperImporter()
                assert importer._processed_urls == set()

    def test_save_processed_url_to_backup(self):
        """Should save URL to backup file."""
        with patch("builtins.open", MagicMock()) as mock_open:
            with patch("json.dump") as mock_json_dump:
                importer = ScraperImporter("/tmp/test.json")
                importer._save_processed_url_to_backup("http://example.com")
                assert "http://example.com" in importer._processed_urls
                mock_json_dump.assert_called_once()

    def test_save_processed_url_continues_on_error(self):
        """Should continue when save fails."""
        with patch("builtins.open", side_effect=Exception("Write error")):
            importer = ScraperImporter("/tmp/test.json")
            importer._save_processed_url_to_backup("http://example.com")
            assert "http://example.com" in importer._processed_urls

    def test_select_adapter_key_returns_rj_for_rj_domain(self):
        """Should return rj_nfe_moderno for RJ domain."""
        importer = ScraperImporter()
        url = "http://www4.fazenda.rj.gov.br/consultaNFCe/..."
        assert importer._select_adapter_key(url) == "rj_nfe_moderno"

    def test_select_adapter_key_returns_default_for_other_domains(self):
        """Should return default for other domains."""
        importer = ScraperImporter()
        url = "http://example.com"
        assert importer._select_adapter_key(url) == "default"

    @patch("backend.app.services.scraper_handler.requests.get")
    def test_import_from_url_with_requests(self, mock_get):
        """Should import from URL using requests."""
        mock_response = Mock()
        mock_response.text = f"<html><h1>Test Store</h1>{ITEMS_TABLE}</html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with patch.object(ScraperImporter, "_save_processed_url_to_backup"):
            importer = ScraperImporter()
            result = importer.import_from_url("http://example.com")

            assert result.seller_name == "Test Store"
            mock_get.assert_called_once_with("http://example.com", timeout=10)

    @patch("backend.app.services.scraper_handler.requests.get")
    def test_import_from_url_falls_back_to_browser(self, mock_get):
        """Should fall back to browser when requests fails."""
        mock_response = Mock()
        mock_response.text = "Acesso bloqueado"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with patch(
            "backend.app.services.scraper_handler.BrowserHTMLFetcher"
        ) as MockFetcher:
            mock_fetcher = Mock()
            mock_fetcher.fetch.return_value = (
                f"<html><h1>Browser Store</h1>{ITEMS_TABLE}</html>"
            )
            MockFetcher.return_value = mock_fetcher

            with patch.object(ScraperImporter, "_save_processed_url_to_backup"):
                importer = ScraperImporter()
                result = importer.import_from_url("http://example.com")

                assert result.seller_name == "Browser Store"
                MockFetcher.assert_called_once()

    @patch("backend.app.services.scraper_handler.requests.get")
    def test_import_from_url_raises_on_browser_block(self, mock_get):
        """Should raise ValueError when browser is also blocked."""
        mock_response = Mock()
        mock_response.text = "Acesso bloqueado"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with patch(
            "backend.app.services.scraper_handler.BrowserHTMLFetcher"
        ) as MockFetcher:
            mock_fetcher = Mock()
            mock_fetcher.fetch.return_value = "Acesso negado ao portal"
            MockFetcher.return_value = mock_fetcher

            importer = ScraperImporter()
            with pytest.raises(ValueError, match="SEFAZ bloqueou o acesso"):
                importer.import_from_url("http://example.com")

    def test_import_from_url_skips_requests_when_force_browser(self):
        """Should skip requests when force_browser is True."""
        with patch("backend.app.services.scraper_handler.requests.get") as mock_get:
            with patch(
                "backend.app.services.scraper_handler.BrowserHTMLFetcher"
            ) as MockFetcher:
                mock_fetcher = Mock()
                mock_fetcher.fetch.return_value = (
                    f"<html><h1>Browser Only</h1>{ITEMS_TABLE}</html>"
                )
                MockFetcher.return_value = mock_fetcher

                with patch.object(ScraperImporter, "_save_processed_url_to_backup"):
                    importer = ScraperImporter()
                    result = importer.import_from_url(
                        "http://example.com", force_browser=True
                    )

                    assert result.seller_name == "Browser Only"
                    mock_get.assert_not_called()
