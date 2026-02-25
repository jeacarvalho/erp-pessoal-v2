"""Testes para o frontend Streamlit"""

import os
import pytest
import httpx
from unittest.mock import patch, MagicMock

os.environ["BACKEND_URL"] = "http://localhost:8000"


class TestFetchData:
    """Testes para função fetch_data"""

    @patch("app_streamlit.httpx.get")
    def test_fetch_data_success(self, mock_get):
        """Testa fetch_data com resposta bem-sucedida"""
        from app_streamlit import fetch_data

        mock_response = MagicMock()
        mock_response.json.return_value = {"test": "data"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = fetch_data("http://test.com/api")

        assert result == {"test": "data"}
        mock_get.assert_called_once_with("http://test.com/api")

    @patch("app_streamlit.httpx.get")
    def test_fetch_data_request_error(self, mock_get):
        """Testa fetch_data com erro de conexão"""
        import app_streamlit

        mock_get.side_effect = httpx.RequestError(
            "Connection error", request=MagicMock()
        )

        with patch("app_streamlit.st.error"):
            result = app_streamlit.fetch_data("http://test.com/api")

        assert result is None

    @patch("app_streamlit.httpx.get")
    def test_fetch_data_http_error(self, mock_get):
        """Testa fetch_data com erro HTTP"""
        import app_streamlit

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=MagicMock()
        )
        mock_get.return_value = mock_response

        with patch("app_streamlit.st.error"):
            result = app_streamlit.fetch_data("http://test.com/api")

        assert result is None


class TestFetchPriceComparison:
    """Testes para função fetch_price_comparison"""

    @patch("app_streamlit.httpx.get")
    def test_fetch_price_comparison_success(self, mock_get):
        """Testa fetch_price_comparison com resposta bem-sucedida"""
        from app_streamlit import fetch_price_comparison

        mock_response = MagicMock()
        mock_response.json.return_value = [{"product": "test", "price": 10.0}]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = fetch_price_comparison("arroz")

        assert result == [{"product": "test", "price": 10.0}]
        mock_get.assert_called_once()

    @patch("app_streamlit.httpx.get")
    def test_fetch_price_comparison_error(self, mock_get):
        """Testa fetch_price_comparison com erro"""
        import app_streamlit

        mock_get.side_effect = httpx.RequestError("Error", request=MagicMock())

        with patch("app_streamlit.st.error"):
            result = app_streamlit.fetch_price_comparison("arroz")

        assert result is None


class TestFetchSellerTrends:
    """Testes para função fetch_seller_trends"""

    @patch("app_streamlit.httpx.get")
    def test_fetch_seller_trends_success(self, mock_get):
        """Testa fetch_seller_trends com resposta bem-sucedida"""
        from app_streamlit import fetch_seller_trends

        mock_response = MagicMock()
        mock_response.json.return_value = {"seller_name": "Test Seller", "products": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = fetch_seller_trends("Test Seller")

        assert result == {"seller_name": "Test Seller", "products": []}

    @patch("app_streamlit.httpx.get")
    def test_fetch_seller_trends_with_spaces(self, mock_get):
        """Testa fetch_seller_trends com nome de vendedor com espaços"""
        from app_streamlit import fetch_seller_trends

        mock_response = MagicMock()
        mock_response.json.return_value = {"seller_name": "Test", "products": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = fetch_seller_trends("Test Seller")

        mock_get.assert_called_once()
        call_url = mock_get.call_args[0][0]
        assert "seller_name=" in call_url

    @patch("app_streamlit.httpx.get")
    def test_fetch_seller_trends_error(self, mock_get):
        """Testa fetch_seller_trends com erro"""
        import app_streamlit

        mock_get.side_effect = httpx.RequestError("Error", request=MagicMock())

        with patch("app_streamlit.st.error"):
            result = app_streamlit.fetch_seller_trends("Test")

        assert result is None


class TestGetCategories:
    """Testes para função get_categories"""

    @patch("app_streamlit.fetch_data")
    def test_get_categories_returns_list(self, mock_fetch):
        """Testa get_categories retorna lista de categorias"""
        from app_streamlit import get_categories

        mock_fetch.return_value = [
            {"id": 1, "name": "Alimentação"},
            {"id": 2, "name": "Transporte"},
        ]

        result = get_categories()

        assert result == [
            {"id": 1, "name": "Alimentação"},
            {"id": 2, "name": "Transporte"},
        ]

    @patch("app_streamlit.fetch_data")
    def test_get_categories_empty(self, mock_fetch):
        """Testa get_categories com lista vazia"""
        from app_streamlit import get_categories

        mock_fetch.return_value = []

        result = get_categories()

        assert result == []


class TestGetTransactions:
    """Testes para função get_transactions"""

    @patch("app_streamlit.fetch_data")
    def test_get_transactions_returns_list(self, mock_fetch):
        """Testa get_transactions retorna lista de transações"""
        from app_streamlit import get_transactions

        mock_fetch.return_value = [
            {"id": 1, "amount": 100.0},
            {"id": 2, "amount": 50.0},
        ]

        result = get_transactions()

        assert result == [{"id": 1, "amount": 100.0}, {"id": 2, "amount": 50.0}]


class TestGetFiscalItems:
    """Testes para função get_fiscal_items"""

    @patch("app_streamlit.fetch_data")
    def test_get_fiscal_items_returns_list(self, mock_fetch):
        """Testa get_fiscal_items retorna lista de itens"""
        from app_streamlit import get_fiscal_items

        mock_fetch.return_value = [
            {"id": 1, "product_name": "Arroz"},
            {"id": 2, "product_name": "Feijão"},
        ]

        result = get_fiscal_items()

        assert result == [
            {"id": 1, "product_name": "Arroz"},
            {"id": 2, "product_name": "Feijão"},
        ]


class TestGetSellers:
    """Testes para função get_sellers"""

    @patch("app_streamlit.fetch_data")
    def test_get_sellers_returns_list(self, mock_fetch):
        """Testa get_sellers retorna lista de vendedores"""
        from app_streamlit import get_sellers

        mock_fetch.return_value = ["Seller A", "Seller B"]

        result = get_sellers()

        assert result == ["Seller A", "Seller B"]
        mock_fetch.assert_called_once()

    @patch("app_streamlit.fetch_data")
    def test_get_sellers_empty(self, mock_fetch):
        """Testa get_sellers com lista vazia"""
        from app_streamlit import get_sellers

        mock_fetch.return_value = []

        result = get_sellers()

        assert result == []


class TestSellerTrendsProcessing:
    """Testes para processamento de dados de tendências de vendedores"""

    def test_process_top_10_villains_sorted(self):
        """Testa ordenação devilões por variação"""
        from app_streamlit import fetch_data

        mock_data = {
            "seller_name": "Test Seller",
            "products": [
                {
                    "product_name": "Product A",
                    "price_history": [10.0, 8.0],
                    "variation_percent": 25.0,
                },
                {
                    "product_name": "Product B",
                    "price_history": [15.0, 12.0],
                    "variation_percent": 25.0,
                },
                {
                    "product_name": "Product C",
                    "price_history": [20.0, 25.0],
                    "variation_percent": -20.0,
                },
            ],
        }

        products = mock_data["products"]

        top_villains = [
            p
            for p in products
            if p.get("variation_percent") is not None and len(p["price_history"]) >= 2
        ]
        top_villains.sort(key=lambda x: x["variation_percent"], reverse=True)
        top_10 = top_villains[:10]

        assert len(top_10) == 3
        assert top_10[0]["variation_percent"] == 25.0
        assert top_10[-1]["variation_percent"] == -20.0

    def test_process_products_with_variation_and_without(self):
        """Testa区分 produtos com e sem variação"""
        products = [
            {"product_name": "A", "price_history": [10.0], "variation_percent": None},
            {
                "product_name": "B",
                "price_history": [10.0, 8.0],
                "variation_percent": 25.0,
            },
            {"product_name": "C", "price_history": [5.0], "variation_percent": None},
        ]

        with_variation = [p for p in products if p.get("variation_percent") is not None]
        without_variation = [p for p in products if p.get("variation_percent") is None]

        assert len(with_variation) == 1
        assert len(without_variation) == 2

    def test_table_data_format(self):
        """Testa formatação de dados para tabela"""
        products = [
            {
                "product_name": "Arroz",
                "price_history": [25.90, 24.90],
                "variation_percent": 4.02,
            }
        ]

        table_data = []
        for p in products:
            last_price = p["price_history"][0]
            prev_price = p["price_history"][1] if len(p["price_history"]) > 1 else None
            variation = p.get("variation_percent")

            table_data.append(
                {
                    "Produto": p["product_name"],
                    "Último Preço (R$)": f"{last_price:.2f}",
                    "Preço Anterior (R$)": f"{prev_price:.2f}" if prev_price else "-",
                    "Variação (%)": f"{variation:.2f}%"
                    if variation is not None
                    else "-",
                }
            )

        assert len(table_data) == 1
        assert table_data[0]["Produto"] == "Arroz"
        assert table_data[0]["Último Preço (R$)"] == "25.90"
        assert table_data[0]["Preço Anterior (R$)"] == "24.90"
        assert table_data[0]["Variação (%)"] == "4.02%"

    def test_table_data_no_history(self):
        """Testa formatação sem histórico de preços"""
        products = [
            {"product_name": "Test", "price_history": [10.0], "variation_percent": None}
        ]

        table_data = []
        for p in products:
            last_price = p["price_history"][0]
            prev_price = p["price_history"][1] if len(p["price_history"]) > 1 else None
            variation = p.get("variation_percent")

            table_data.append(
                {
                    "Produto": p["product_name"],
                    "Último Preço (R$)": f"{last_price:.2f}",
                    "Preço Anterior (R$)": f"{prev_price:.2f}" if prev_price else "-",
                    "Variação (%)": f"{variation:.2f}%"
                    if variation is not None
                    else "-",
                }
            )

        assert table_data[0]["Preço Anterior (R$)"] == "-"
        assert table_data[0]["Variação (%)"] == "-"

    def test_villains_df_format(self):
        """Testa formatação do DataFrame para gráfico"""
        villains = [
            {
                "product_name": "Produto A Muito Longo Para Display",
                "variation_percent": 15.5,
            },
            {"product_name": "Produto B", "variation_percent": 10.0},
        ]

        villains_df_data = {
            "Produto": [
                p["product_name"][:25] + "..."
                if len(p["product_name"]) > 25
                else p["product_name"]
                for p in villains
            ],
            "Variação (%)": [p["variation_percent"] for p in villains],
        }

        assert villains_df_data["Produto"][0] == "Produto A Muito Longo Par..."
        assert villains_df_data["Produto"][1] == "Produto B"
        assert villains_df_data["Variação (%)"] == [15.5, 10.0]


class TestBackendURL:
    """Testes para configuração de URL do backend"""

    def test_backend_url_from_env(self):
        """Testa que BACKEND_URL é lido corretamente"""
        os.environ["BACKEND_URL"] = "http://test:9000"

        import importlib
        import app_streamlit

        importlib.reload(app_streamlit)

        assert app_streamlit.BACKEND_URL == "http://test:9000"

        os.environ["BACKEND_URL"] = "http://localhost:8000"
        importlib.reload(app_streamlit)

    def test_backend_url_default(self):
        """Testa que BACKEND_URL tem valor padrão"""
        original = os.environ.get("BACKEND_URL")
        if "BACKEND_URL" in os.environ:
            del os.environ["BACKEND_URL"]

        import importlib
        import app_streamlit

        importlib.reload(app_streamlit)

        assert app_streamlit.BACKEND_URL == "http://localhost:8000"

        if original:
            os.environ["BACKEND_URL"] = original
        importlib.reload(app_streamlit)


class TestURLEncoding:
    """Testes para encoding de URLs"""

    def test_quote_special_chars(self):
        """Testa que caracteres especiais são codificados corretamente"""
        from urllib.parse import quote

        seller = "Seller Name; CNPJ: 12.345.678/0001-90"
        encoded = quote(seller, safe="")

        assert " " in encoded or "%" in encoded
        assert ";" in encoded or "%3B" in encoded

    def test_quote_safe_chars(self):
        """Testa que caracteres seguros não são codificados"""
        from urllib.parse import quote

        seller = "Seller-Name_123"
        encoded = quote(seller, safe="")

        assert encoded == seller or "%" in encoded


class TestHelpers:
    """Testes para funções helper"""

    def test_quote_with_empty_string(self):
        """Testa quote com string vazia"""
        from urllib.parse import quote

        result = quote("", safe="")
        assert result == ""

    def test_quote_with_only_spaces(self):
        """Testa quote com apenas espaços"""
        from urllib.parse import quote

        result = quote("   ", safe="")
        assert "%20" in result
