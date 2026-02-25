from __future__ import annotations

import pytest

from backend.app.services.flyer_analyzer import (
    FlyerAnalyzer,
    ExtractedOffer,
    group_offers_by_proximity,
)


class TestFlyerAnalyzer:
    """Testes para o analisador de encartes."""

    def test_extract_price_rs_format(self) -> None:
        """Testa extração de preço no formato R$ X,XX."""
        analyzer = FlyerAnalyzer()

        result = analyzer._extract_price("R$ 12,90")
        assert result == 12.90

        result = analyzer._extract_price("R$ 5,50")
        assert result == 5.50

    def test_extract_price_por_format(self) -> None:
        """Testa extração de preço no formato POR X,XX."""
        analyzer = FlyerAnalyzer()

        result = analyzer._extract_price("POR 9,90")
        assert result == 9.90

    def test_extract_price_reais_format(self) -> None:
        """Testa extração de preço no formato X,XX reais."""
        analyzer = FlyerAnalyzer()

        result = analyzer._extract_price("15.90 reais")
        assert result == 15.90

    def test_extract_price_no_price(self) -> None:
        """Testa texto sem preço."""
        analyzer = FlyerAnalyzer()

        result = analyzer._extract_price("Leite Integral")
        assert result is None

    def test_extract_price_with_spaces(self) -> None:
        """Testa preço com espaços."""
        analyzer = FlyerAnalyzer()

        result = analyzer._extract_price("R$ 10 , 00")
        assert result == 10.0


class TestExtractedOffer:
    """Testes para a classe ExtractedOffer."""

    def test_to_dict(self) -> None:
        """Testa conversão para dicionário."""
        offer = ExtractedOffer("Leite Integral 1L", 4.99)
        result = offer.to_dict()

        assert result == {"description": "Leite Integral 1L", "price": 4.99}


class TestGroupOffersByProximity:
    """Testes para grouping de ofertas."""

    def test_empty_list(self) -> None:
        """Testa lista vazia."""
        result = group_offers_by_proximity([])
        assert result == []

    def test_single_offer(self) -> None:
        """Testa oferta única."""
        offers = [ExtractedOffer("Leite", 5.0)]
        result = group_offers_by_proximity(offers)

        assert len(result) == 1
        assert result[0].description == "Leite"

    def test_similar_descriptions(self) -> None:
        """Testa descrições similares."""
        offers = [
            ExtractedOffer("Leite Integral 1L", 5.0),
            ExtractedOffer("Leite Integral", 4.50),
        ]
        result = group_offers_by_proximity(offers)

        assert len(result) == 1
        assert result[0].price == 4.50

    def test_different_descriptions(self) -> None:
        """Testa descrições diferentes."""
        offers = [
            ExtractedOffer("Leite Integral", 5.0),
            ExtractedOffer("Pão de Forma", 3.50),
        ]
        result = group_offers_by_proximity(offers)

        assert len(result) == 2
