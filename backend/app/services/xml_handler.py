from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Optional
from uuid import uuid4
import xml.etree.ElementTree as ET


@dataclass
class ParsedItem:
    """Representa um item de produto extraído de uma nota."""

    name: str
    quantity: float
    unit: str
    unit_price: float
    total_price: float


@dataclass
class ParsedNote:
    """Representa uma nota fiscal extraída de XML ou scraping."""

    date: date
    seller_name: str
    total_amount: float
    access_key: str
    items: List[ParsedItem]


class XMLProcessor:
    """Processador de XML de NF-e/NFC-e.

    Usa `xml.etree.ElementTree` para interpretar o XML e extrair:
    - Data
    - Nome do estabelecimento
    - Valor total
    - Itens (Nome, Quantidade, Unidade, Preço unitário, Preço total)
    """

    def parse(self, xml_content: str | bytes) -> ParsedNote:
        """Processa o conteúdo XML e retorna uma `ParsedNote`."""

        root = ET.fromstring(xml_content)

        # Normaliza namespaces: usamos buscas por sufixo dos nomes das tags.
        def find_first(element: ET.Element, tag_suffix: str) -> Optional[ET.Element]:
            for el in element.iter():
                if el.tag.endswith(tag_suffix):
                    return el
            return None

        def findall(element: ET.Element, tag_suffix: str) -> List[ET.Element]:
            return [el for el in element.iter() if el.tag.endswith(tag_suffix)]

        # Data de emissão: dhEmi (formato completo) ou dEmi (apenas data).
        date_text: Optional[str] = None
        dh_emi_el = find_first(root, "dhEmi")
        d_emi_el = find_first(root, "dEmi")
        if dh_emi_el is not None and dh_emi_el.text:
            date_text = dh_emi_el.text[:10]
        elif d_emi_el is not None and d_emi_el.text:
            date_text = d_emi_el.text[:10]

        if not date_text:
            raise ValueError("Data de emissão não encontrada no XML.")

        year, month, day = map(int, date_text.split("-"))
        emission_date = date(year, month, day)

        # Nome do estabelecimento (emit/xNome).
        seller_name_el = None
        emit_el = find_first(root, "emit")
        if emit_el is not None:
            for child in emit_el:
                if child.tag.endswith("xNome"):
                    seller_name_el = child
                    break

        if seller_name_el is None or not seller_name_el.text:
            raise ValueError("Nome do estabelecimento não encontrado no XML.")

        seller_name = seller_name_el.text.strip()

        # Valor total da nota (total/ICMSTot/vNF).
        v_nf_el = find_first(root, "vNF")
        if v_nf_el is None or not v_nf_el.text:
            raise ValueError("Valor total da nota não encontrado no XML.")

        total_amount = float(v_nf_el.text.replace(",", "."))

        # Chave de acesso: chNFe ou atributo Id do infNFe.
        access_key: Optional[str] = None
        ch_nfe_el = find_first(root, "chNFe")
        if ch_nfe_el is not None and ch_nfe_el.text:
            access_key = ch_nfe_el.text.strip()
        else:
            inf_nfe_el = find_first(root, "infNFe")
            if inf_nfe_el is not None:
                access_key_attr = inf_nfe_el.attrib.get("Id")
                if access_key_attr:
                    access_key = access_key_attr.strip()

        if not access_key:
            access_key = f"XML-{uuid4().hex}"

        # Itens: cada <det><prod>.
        items: List[ParsedItem] = []
        for det_el in findall(root, "det"):
            prod_el: Optional[ET.Element] = None
            for child in det_el:
                if child.tag.endswith("prod"):
                    prod_el = child
                    break
            if prod_el is None:
                continue

            def _get_text(suffix: str) -> Optional[str]:
                for child in prod_el:  # type: ignore[union-attr]
                    if child.tag.endswith(suffix) and child.text:
                        return child.text.strip()
                return None

            name = _get_text("xProd") or ""
            q_com_text = _get_text("qCom") or "0"
            u_com = _get_text("uCom") or ""
            v_un_com_text = _get_text("vUnCom") or "0"
            v_prod_text = _get_text("vProd") or v_un_com_text

            quantity = float(q_com_text.replace(",", "."))
            unit_price = float(v_un_com_text.replace(",", "."))
            total_price = float(v_prod_text.replace(",", "."))

            items.append(
                ParsedItem(
                    name=name,
                    quantity=quantity,
                    unit=u_com,
                    unit_price=unit_price,
                    total_price=total_price,
                )
            )

        if not items:
            raise ValueError("Nenhum item de produto encontrado no XML.")

        return ParsedNote(
            date=emission_date,
            seller_name=seller_name,
            total_amount=total_amount,
            access_key=access_key,
            items=items,
        )


__all__ = ["XMLProcessor", "ParsedItem", "ParsedNote"]

