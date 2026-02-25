import io
import re
from typing import List, Optional

import easyocr
import numpy as np
from PIL import Image
from PyPDF2 import PdfReader


class ExtractedOffer:
    """Representa uma oferta extraída de um encarte."""

    def __init__(self, description: str, price: float):
        self.description = description
        self.price = price

    def to_dict(self) -> dict:
        return {"description": self.description, "price": self.price}


class FlyerAnalyzer:
    """Analisador de encartes usando OCR para extração de ofertas."""

    _reader: Optional[easyocr.Reader] = None

    def __init__(self, languages: List[str] = ["pt", "en"]):
        self.languages = languages

    @classmethod
    def _get_reader(cls, languages: List[str]) -> easyocr.Reader:
        if cls._reader is None:
            cls._reader = easyocr.Reader(languages, gpu=False)
        return cls._reader

    def extract_offers(self, file_bytes: bytes) -> List[ExtractedOffer]:
        """Extrai ofertas (produto + preço) de um encarte (imagem ou PDF)."""

        if file_bytes[:5] == b"%PDF-":
            return self._extract_from_pdf(file_bytes)

        return self._extract_from_image(file_bytes)

    def _extract_from_image(self, image_bytes: bytes) -> List[ExtractedOffer]:
        """Extrai ofertas de uma imagem."""
        image = Image.open(io.BytesIO(image_bytes))
        image_array = np.array(image)

        reader = self._get_reader(self.languages)
        results = reader.readtext(image_array)

        return self._parse_ocr_results(results)

    def _extract_from_pdf(self, pdf_bytes: bytes) -> List[ExtractedOffer]:
        """Extrai ofertas de um PDF (converte cada página para imagem)."""
        all_offers: List[ExtractedOffer] = []

        try:
            from pdf2image import convert_from_bytes

            reader = PdfReader(io.BytesIO(pdf_bytes))
            num_pages = len(reader.pages)

            ocr_reader = self._get_reader(self.languages)

            # Process up to first 3 pages (most likely to have offers)
            for page_num in range(1, min(num_pages + 1, 4)):
                try:
                    images = convert_from_bytes(
                        pdf_bytes, dpi=150, first_page=page_num, last_page=page_num
                    )
                    if images:
                        img_array = np.array(images[0])
                        results = ocr_reader.readtext(img_array)
                        page_offers = self._parse_ocr_results(results)
                        all_offers.extend(page_offers)
                except Exception:
                    continue

        except Exception as e:
            pass

        return all_offers

    def _pdf_page_to_image(self, page) -> Optional[np.ndarray]:
        """Converte uma página de PDF para imagem."""
        try:
            from pdf2image import convert_from_bytes

            images = convert_from_bytes(
                page.get_object().get_data(), dpi=200, first_page=1, last_page=1
            )
            if images:
                return np.array(images[0])
        except Exception:
            pass

        try:
            xObject = page.get_object()["/Resources"]["/XObject"].get_object()
            for obj in xObject:
                if xObject[obj]["/Subtype"] == "/Image":
                    data = xObject[obj].get_data()
                    if "/Filter" in xObject[obj]:
                        if xObject[obj]["/Filter"] == "/DCTDecode":
                            img = Image.open(io.BytesIO(data))
                            return np.array(img)
        except Exception:
            pass

        return None

    def _parse_ocr_results(self, results: list) -> List[ExtractedOffer]:
        """Parseia resultados do OCR para ofertas.

        Abordagem: agrupar por Y (linhas) e parear produto (esquerda) com preço (direita)
        """

        GARBAGE_TERMS = [
            "IIROL",
            "BFUNG",
            "KG*EXCETO",
            "SKG*EXCETO",
            "GRANEL",
            "EXCETO",
            "SUL",
            "NORTE",
            "FLUMINENSE",
            "SULFL",
            "TIROL",
            "GODAM",
            "KG'E",
            "KG'EXCETO",
            "A GRANEL",
            "OU",
            "A.",
            "OU.",
            "PEÇA",
            "CONGELADO",
            "MADURA",
            "PERA",
            "WILLIAMS",
            "MACA",
            "GALA",
            "CAPEL",
            "CARAVELAS",
            "IKG*EXCETO",
            "VERELAC",
            "LAR",
            "AMEIXA",
            "PERDIGAO",
            "SUL FLUMINENSE",
            "GRANEL KG",
            "X",
            "KG",
            "POR",
            "RS",
            "LONGA",
            "VIDA",
            "INTEGRAL",
            "EXTRA",
            "PORTUGUES",
        ]

        items = []
        for bbox, text, confidence in results:
            if confidence < 0.20:
                continue

            cleaned = text.strip()
            if not cleaned or len(cleaned) < 2:
                continue

            x = int(bbox[0][0])
            y = int(bbox[0][1])
            price = self._extract_price(cleaned)

            items.append({"x": x, "y": y, "text": cleaned, "price": price})

        # Instead of grouping by Y bucket, find products and find closest prices in nearby Y
        products = []
        all_prices = []

        for item in items:
            if item["price"] and item["price"] > 2.0:
                all_prices.append(item)
            elif not item["price"]:
                txt_upper = item["text"].upper()
                if (
                    not any(g in txt_upper for g in GARBAGE_TERMS)
                    and len(item["text"]) > 2
                    and item["x"] < 500  # Include products from multiple columns
                ):
                    products.append(item)

        offers = []

        for prod in products:
            best_price = None
            best_score = float("inf")

            for price in all_prices:
                if price["x"] <= prod["x"]:
                    continue

                y_diff = abs(price["y"] - prod["y"])
                x_diff = price["x"] - prod["x"]

                if y_diff < 80:
                    score = y_diff * 10 + x_diff
                    if score < best_score:
                        best_score = score
                        best_price = price["price"]

            if best_price:
                offers.append(ExtractedOffer(prod["text"], best_price))

        # Deduplicate
        product_best = {}
        for o in offers:
            key = o.description.lower()[:20]
            if key not in product_best or o.price < product_best[key].price:
                product_best[key] = o

        return list(product_best.values())

    def _extract_price(self, text: str) -> Optional[float]:
        """Extrai preço de uma string."""
        text_only_price = re.sub(r"^(POR|por)\s*", "", text).strip()

        patterns = [
            r"R\$\s*(\d+[,.]?\d*)",
            r"(\d+[,.]?\d*)\s*(?:reais|R\$)",
            r"(?:POR|por|R\$)\s*(\d+[,.]?\d*)",
            r"(\d+[,.]?\d*)$",
        ]

        for pattern in patterns:
            match = re.search(pattern, text_only_price)
            if match:
                price_str = match.group(1).replace(",", ".")
                try:
                    return float(price_str)
                except ValueError:
                    continue

        return None


def group_offers_by_proximity(offers: List[ExtractedOffer]) -> List[ExtractedOffer]:
    """Agrupa ofertas próximas baseado em heurísticas simples."""
    if not offers:
        return []

    grouped: List[ExtractedOffer] = []
    current_group: List[ExtractedOffer] = []

    for offer in offers:
        if not current_group:
            current_group.append(offer)
        else:
            last_offer = current_group[-1]
            if _are_similar(last_offer.description, offer.description):
                current_group.append(offer)
            else:
                if len(current_group) == 1:
                    grouped.append(last_offer)
                else:
                    best = _pick_best_offer(current_group)
                    grouped.append(best)
                current_group = [offer]

    if current_group:
        if len(current_group) == 1:
            grouped.append(current_group[0])
        else:
            best = _pick_best_offer(current_group)
            grouped.append(best)

    return grouped


def _are_similar(desc1: str, desc2: str) -> bool:
    """Verifica se duas descrições são similares."""
    words1 = set(desc1.lower().split())
    words2 = set(desc2.lower().split())
    intersection = words1 & words2
    union = words1 | words2
    if not union:
        return False
    return len(intersection) / len(union) > 0.5


def _pick_best_offer(offers: List[ExtractedOffer]) -> ExtractedOffer:
    """Seleciona a melhor oferta de um grupo (menor preço ou mais detalhada)."""
    if len(offers) == 1:
        return offers[0]

    min_price = min(o.price for o in offers)
    cheapest = [o for o in offers if o.price == min_price]

    if len(cheapest) == 1:
        return cheapest[0]

    return max(cheapest, key=lambda o: len(o.description.split()))
