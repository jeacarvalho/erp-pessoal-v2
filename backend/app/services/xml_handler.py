from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Optional
from uuid import uuid4
import xml.etree.ElementTree as ET
import logging

logger = logging.getLogger(__name__)


@dataclass
class ParsedItem:
    """Representa um item de produto extraído de uma nota."""

    name: str
    quantity: float
    unit: str
    unit_price: float
    total_price: float
    ean: Optional[str] = None


@dataclass
class ParsedNote:
    """Representa uma nota fiscal extraída de XML ou scraping."""

    date: date
    seller_name: str
    seller_tax_id: str
    total_amount: float
    access_key: str
    items: List[ParsedItem]
    seller_address: Optional[str] = None

    def __post_init__(self):
        if not self.seller_tax_id:
            import uuid

            self.seller_tax_id = f"UNKNOWN-{uuid.uuid4().hex[:8]}"


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

        # Define namespace para NF-e
        namespaces = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

        # Funções auxiliares para busca considerando namespaces
        def find_first_with_ns(
            element: ET.Element, tag_suffix: str
        ) -> Optional[ET.Element]:
            # Primeiro tenta encontrar com namespace
            xpath = f".//nfe:{tag_suffix}"
            elements = element.findall(xpath, namespaces)
            if elements:
                return elements[0]

            # Depois tenta encontrar sem namespace (fallback)
            for el in element.iter():
                if el.tag.endswith(tag_suffix):
                    return el
            return None

        def findall_with_ns(element: ET.Element, tag_suffix: str) -> List[ET.Element]:
            # Primeiro tenta encontrar com namespace
            xpath = f".//nfe:{tag_suffix}"
            elements = element.findall(xpath, namespaces)
            if elements:
                return elements

            # Depois tenta encontrar sem namespace (fallback)
            return [el for el in element.iter() if el.tag.endswith(tag_suffix)]

        # Data de emissão: ide/dhEmi
        date_text: Optional[str] = None
        dh_emi_el = find_first_with_ns(root, "dhEmi")
        if dh_emi_el is not None and dh_emi_el.text:
            # Format is YYYY-MM-DDTHH:MM:SS, extract date part
            date_text = dh_emi_el.text[:10]

        if not date_text:
            raise ValueError("Data de emissão não encontrada no XML.")

        year, month, day = map(int, date_text.split("-"))
        emission_date = date(year, month, day)

        # Vendedor: emit/xNome e emit/CNPJ
        seller_name_el = None
        seller_cnpj_el = None
        seller_address = None
        emit_el = find_first_with_ns(root, "emit")
        if emit_el is not None:
            xnome_el = find_first_with_ns(emit_el, "xNome")
            if xnome_el is not None:
                seller_name_el = xnome_el

            cnpj_el = find_first_with_ns(emit_el, "CNPJ")
            if cnpj_el is not None and cnpj_el.text:
                seller_cnpj_el = cnpj_el.text.strip()

            ender_emit_el = find_first_with_ns(emit_el, "enderEmit")
            if ender_emit_el is not None:
                xlgr_el = find_first_with_ns(ender_emit_el, "xLgr")
                nro_el = find_first_with_ns(ender_emit_el, "nro")
                xbairro_el = find_first_with_ns(ender_emit_el, "xBairro")
                xmun_el = find_first_with_ns(ender_emit_el, "xMun")
                uf_el = find_first_with_ns(ender_emit_el, "UF")

                address_parts = []
                if xlgr_el is not None and xlgr_el.text:
                    address_parts.append(xlgr_el.text.strip())
                if nro_el is not None and nro_el.text:
                    address_parts.append(nro_el.text.strip())
                if xbairro_el is not None and xbairro_el.text:
                    address_parts.append(xbairro_el.text.strip())
                if xmun_el is not None and xmun_el.text:
                    address_parts.append(xmun_el.text.strip())
                if uf_el is not None and uf_el.text:
                    address_parts.append(uf_el.text.strip())

                if address_parts:
                    seller_address = ", ".join(address_parts)

        if seller_name_el is None or not seller_name_el.text:
            raise ValueError("Nome do vendedor não encontrado no XML.")

        if seller_cnpj_el is None:
            import uuid

            seller_cnpj_el = f"UNKNOWN-{uuid.uuid4().hex[:8]}"
            logger.warning(
                f"CNPJ não encontrado no XML. Gerado ID temporário: {seller_cnpj_el}"
            )

        # Clean up the seller name by removing newlines and extra whitespace
        raw_seller_name = seller_name_el.text.strip() if seller_name_el.text else ""
        # Handle both literal '\n' (backslash followed by n) and actual newlines
        cleaned_seller_name = (
            raw_seller_name.replace("\\n", " ").replace("\n", " ").replace("\r", " ")
        )
        seller_name = " ".join(cleaned_seller_name.split())

        # Valor Total: total/ICMSTot/vNF
        v_nf_el = find_first_with_ns(root, "vNF")
        if v_nf_el is None or not v_nf_el.text:
            raise ValueError("Valor total da nota não encontrado no XML.")

        total_amount = float(v_nf_el.text.replace(",", "."))

        # Chave de acesso do atributo Id na tag infNFe
        access_key: Optional[str] = None
        inf_nfe_el = find_first_with_ns(root, "infNFe")
        if inf_nfe_el is not None:
            access_key_attr = inf_nfe_el.attrib.get("Id")
            if access_key_attr:
                # Remover prefixo "NFe" se existir
                access_key = access_key_attr.replace("NFe", "").strip()

        if not access_key:
            access_key = f"XML-{uuid4().hex}"

        # Itens: iterar sobre as tags det
        items: List[ParsedItem] = []
        for det_el in findall_with_ns(root, "det"):
            prod_el: Optional[ET.Element] = find_first_with_ns(det_el, "prod")
            if prod_el is None:
                continue

            # Extrair informações do produto
            def _get_text_from_prod(suffix: str) -> Optional[str]:
                for child in prod_el:
                    # Check if tag ends with suffix, considering possible namespace
                    tag_name = child.tag.split("}")[
                        -1
                    ]  # Remove namespace prefix if present
                    if tag_name == suffix and child.text:
                        return child.text.strip()
                return None

            name = _get_text_from_prod("xProd") or ""
            ean = _get_text_from_prod("cEAN") or None
            q_com_text = _get_text_from_prod("qCom") or "0"
            v_un_com_text = _get_text_from_prod("vUnCom") or "0"
            v_prod_text = _get_text_from_prod("vProd") or v_un_com_text
            u_com = _get_text_from_prod("uCom") or ""

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
                    ean=ean,
                )
            )

        if not items:
            raise ValueError("Nenhum item de produto encontrado no XML.")

        return ParsedNote(
            date=emission_date,
            seller_name=seller_name,
            seller_tax_id=seller_cnpj_el,
            seller_address=seller_address,
            total_amount=total_amount,
            access_key=access_key,
            items=items,
        )


__all__ = ["XMLProcessor", "ParsedItem", "ParsedNote"]
