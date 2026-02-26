import pytest
from unittest.mock import MagicMock, patch

from app.services.price_comparator import PriceComparator, ComparisonResult


class TestPriceComparator:
    def test_clean_product_name_basic(self):
        comparator = PriceComparator()

        assert (
            comparator.clean_product_name("Arroz Integral 5kg") == "arroz integral 5kg"
        )
        assert comparator.clean_product_name("Leite LONGÁ VIDA") == "leite longá vida"
        assert comparator.clean_product_name("") == ""
        assert comparator.clean_product_name("  ") == ""

    def test_clean_product_name_removes_special_chars(self):
        comparator = PriceComparator()

        result = comparator.clean_product_name("Feijão! @#$% Carijó")
        assert "!" not in result
        assert "@" not in result
        assert "#" not in result

    def test_find_match_with_exact_product(self):
        comparator = PriceComparator()

        mock_item = MagicMock()
        mock_item.product_name = "Arroz Integral"
        mock_item.unit_price = 15.00

        mock_items = [mock_item]

        with patch("app.repositories.FiscalItemRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_product_name.return_value = mock_items
            mock_repo_class.return_value = mock_repo

            mock_query = MagicMock()
            mock_query.all.return_value = [mock_item]
            mock_session = MagicMock()
            mock_session.query.return_value = mock_query

            result = comparator.find_match("Arroz Integral", mock_session)

            assert result is not None
            items, matched_name = result
            assert matched_name == "Arroz Integral"

    def test_find_match_no_match_due_to_stop_words(self):
        comparator = PriceComparator()

        with patch("app.services.price_comparator.FiscalItem") as mock_fiscal_item:
            mock_query = MagicMock()
            mock_query.all.return_value = []
            mock_session = MagicMock()
            mock_session.query.return_value = mock_query

            result = comparator.find_match("kg ml l", mock_session)

            assert result is None

    def test_find_match_low_score_returns_none(self):
        comparator = PriceComparator(min_match_score=0.5)

        mock_item = MagicMock()
        mock_item.product_name = "Detergente"
        mock_item.unit_price = 3.00

        with patch("app.services.price_comparator.FiscalItem") as mock_fiscal_item:
            mock_query = MagicMock()
            mock_query.all.return_value = [mock_item]
            mock_session = MagicMock()
            mock_session.query.return_value = mock_query

            result = comparator.find_match("Arroz", mock_session)

            assert result is None

    def test_compare_returns_comparison_result(self):
        comparator = PriceComparator()

        mock_item = MagicMock()
        mock_item.product_name = "Leite"
        mock_item.unit_price = 6.00

        mock_items = [mock_item, mock_item, mock_item]

        with patch.object(comparator, "find_match", return_value=(mock_items, "Leite")):
            result = comparator.compare("Leite", 5.00, MagicMock())

            assert result is not None
            assert result.is_deal is True
            assert result.base_avg_price == 6.00
            assert result.savings_percent == 16.67

    def test_compare_not_a_deal(self):
        comparator = PriceComparator()

        mock_item = MagicMock()
        mock_item.product_name = "Leite"
        mock_item.unit_price = 4.00

        mock_items = [mock_item]

        with patch.object(comparator, "find_match", return_value=(mock_items, "Leite")):
            result = comparator.compare("Leite", 5.00, MagicMock())

            assert result is not None
            assert result.is_deal is False
            assert result.base_avg_price == 4.00
            assert result.savings_percent is None

    def test_compare_batch(self):
        comparator = PriceComparator()

        mock_item = MagicMock()
        mock_item.product_name = "Arroz"
        mock_item.unit_price = 10.00

        offers = [
            ("Arroz", 8.00),
            ("Feijão", 7.00),
        ]

        with patch.object(comparator, "compare") as mock_compare:
            mock_compare.side_effect = [
                ComparisonResult(True, 10.00, [], "Arroz", 20.0),
                None,
            ]

            results = comparator.compare_batch(offers, MagicMock())

            assert len(results) == 1
            assert results[0].matched_name == "Arroz"


class TestComparisonResult:
    def test_dataclass_creation(self):
        mock_items = [MagicMock()]

        result = ComparisonResult(
            is_deal=True,
            base_avg_price=15.50,
            matched_items=mock_items,
            matched_name="Arroz",
            savings_percent=10.0,
        )

        assert result.is_deal is True
        assert result.base_avg_price == 15.50
        assert result.matched_items == mock_items
        assert result.matched_name == "Arroz"
        assert result.savings_percent == 10.0
