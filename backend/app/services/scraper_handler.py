from __future__ import annotations

from datetime import date
import json
import os
import re
from typing import Dict, List, Type
from uuid import uuid4

import requests
from bs4 import BeautifulSoup

from .xml_handler import ParsedItem, ParsedNote
from .browser_fetcher import BrowserHTMLFetcher
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _looks_like_sefaz_block_page(html: str) -> bool:
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True).lower()
    return "acesso negado ao portal" in text or "acesso bloqueado" in text


class BaseSefazAdapter:
    """Adapter base para diferentes layouts de páginas de NFC-e das SEFAZ estaduais.

    Cada estado pode ter uma estrutura de HTML diferente. Este adapter define a
    interface que implementações específicas devem seguir.
    """

    def parse(self, html: str) -> ParsedNote:
        """Extrai dados da nota a partir do HTML."""
        raise NotImplementedError


class DefaultSefazAdapter(BaseSefazAdapter):
    """Adapter genérico para páginas de NFC-e.

    Esta implementação tenta encontrar:
    - Data da compra
    - Nome do estabelecimento
    - Valor total
    - Tabela de itens (nome, quantidade, unidade, preço unitário, preço total)

    Como os layouts variam bastante, este adapter é propositalmente genérico e
    focado em oferecer um ponto de extensão. Em produção, recomenda-se criar
    adapters específicos por UF.
    """

    def parse(self, html: str) -> ParsedNote:
        soup = BeautifulSoup(html, "html.parser")

        # Detecção de páginas de bloqueio / acesso negado (ex.: SEFAZ-RJ).
        normalized_text = soup.get_text(" ", strip=True).lower()
        if "acesso negado ao portal" in normalized_text or "acesso bloqueado" in normalized_text:
            raise ValueError(
                "Acesso à página da NFC-e foi negado pela SEFAZ. Conteúdo de nota não disponível."
            )

        # Tentativa genérica de localizar informações básicas
        # (em um cenário real, isso seria ajustado por estado).
        seller_name = self._extract_seller_name(soup)
        total_amount = self._extract_total_amount(soup)
        emission_date = self._extract_date(soup)

        items = self._extract_items(soup)

        access_key = self._extract_access_key(soup)

        return ParsedNote(
            date=emission_date,
            seller_name=seller_name,
            total_amount=total_amount,
            access_key=access_key,
            items=items,
        )

    def _extract_seller_name(self, soup: BeautifulSoup) -> str:
        # Procura pelo elemento txtTopo com id u20 que contém o nome do vendedor
        seller_div = soup.find("div", {"class": "txtTopo", "id": "u20"})
        if seller_div:
            seller_name = seller_div.get_text(strip=True)
            logger.info(f"[fiscal-items] seller_name lido: {seller_name}")
            
            # Procura pelo CNPJ que está na div seguinte
            cnpj_div = seller_div.find_next_sibling("div", class_="text")
            if cnpj_div:
                cnpj_text = cnpj_div.get_text(strip=True)
                if "CNPJ:" in cnpj_text.upper():
                    return f"{seller_name}; {cnpj_text}"
            
            return seller_name
        
        # Se não encontrar o formato específico, tenta métodos alternativos
        for tag_name in ("h1", "h2"):
            tag = soup.find(tag_name)
            if tag and tag.get_text(strip=True):
                return tag.get_text(strip=True)
        
        return "Estabelecimento Desconhecido"

    def _extract_access_key(self, soup: BeautifulSoup) -> str:
        # First, try to find the access key using specific HTML elements
        # Look for elements near "Chave de acesso" text
        import re
        
        # Look for span elements with class 'chave' which often contain the access key
        chave_spans = soup.find_all('span', class_='chave')
        if chave_spans:
            raw_key = chave_spans[0].get_text(strip=True)
            # Clean up the key (remove spaces, check if it's 44 digits)
            clean_key = re.sub(r'\s+', '', raw_key)
            if len(clean_key) == 44 and clean_key.isdigit():
                # Format the key nicely with spaces every 4 digits
                formatted_key = ' '.join([clean_key[i:i+4] for i in range(0, len(clean_key), 4)])
                return formatted_key
        
        # Also look for strong tags that might contain "Chave de acesso" followed by the key
        strong_tags = soup.find_all('strong')
        for tag in strong_tags:
            if 'chave de acesso' in tag.get_text(strip=True).lower():
                # Look for the next sibling that might contain the key
                next_sibling = tag.next_sibling
                while next_sibling and len(next_sibling.strip()) == 0:
                    next_sibling = next_sibling.next_sibling
                if next_sibling and isinstance(next_sibling, str):
                    # Extract potential key from the text following the "Chave de acesso" tag
                    potential_key = next_sibling.strip()
                    # Clean up the key
                    clean_key = re.sub(r'[^\d\s]', '', potential_key)  # Keep only digits and spaces
                    clean_key = re.sub(r'\s+', '', clean_key)  # Remove all spaces temporarily
                    if len(clean_key) == 44 and clean_key.isdigit():
                        # Format the key nicely with spaces every 4 digits
                        formatted_key = ' '.join([clean_key[i:i+4] for i in range(0, len(clean_key), 4)])
                        return formatted_key
                
                # Also check parent's siblings
                parent = tag.parent
                if parent:
                    # Look for spans or other elements within the parent that might contain the key
                    for child in parent.children:
                        if child != tag and hasattr(child, 'get_text'):
                            child_text = child.get_text(strip=True)
                            if child_text and len(child_text) >= 44:
                                # Clean up the key
                                clean_key = re.sub(r'\s+', '', child_text)
                                if len(clean_key) == 44 and clean_key.isdigit():
                                    # Format the key nicely with spaces every 4 digits
                                    formatted_key = ' '.join([clean_key[i:i+4] for i in range(0, len(clean_key), 4)])
                                    return formatted_key
        
        # If the specific element approach didn't work, fall back to the original text-based approach
        text = soup.get_text(" ", strip=True)
        
        # Procura por padrões de chave de acesso (44 dígitos)
        # Procura por padrões com espaços ou sem espaços (ex: 3326 0210 6976 9700 0660 6510 7000 3680 6612 6649 4182 ou 33260210697697000660651070003680661266494182)
        patterns = [
            r'Chave\s*de\s*Acesso[^\d]*([0-9\s]{40,50})',  # "Chave de Acesso" followed by digits/spaces
            r'Chave\s*de\s*acesso[^\d]*([0-9\s]{40,50})',  # "Chave de acesso" followed by digits/spaces
            r'([0-9\s]{40,50})',  # Just the 44 digits pattern (with possible spaces)
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Clean up the matched string to keep only digits and remove extra spaces
                clean_match = re.sub(r'\s+', '', match.strip())
                if len(clean_match) == 44 and clean_match.isdigit():
                    # Format the key nicely with spaces every 4 digits
                    formatted_key = ' '.join([clean_match[i:i+4] for i in range(0, len(clean_match), 4)])
                    return formatted_key
        
        # If no key found, generate a UUID-based key as fallback
        return f"SCRAPING-{uuid4().hex}"

    def _extract_total_amount(self, soup: BeautifulSoup) -> float:
        # Busca por textos que contenham "Total" e um valor numérico próximo.
        text = soup.get_text(" ", strip=True)
        # Heurística simplificada: em produção, regex mais robusta.
        for token in text.split():
            token_norm = token.replace(".", "").replace(",", ".")
            try:
                value = float(token_norm)
                if value > 0:
                    return value
            except ValueError:
                continue
        return 0.0

    def _extract_date(self, soup: BeautifulSoup) -> date:
        # Procura por padrões de data e hora no HTML, como no exemplo:
        # "Emissão: 11/02/2026 07:35:22-03:00"
        import re
        
        # Primeiro tenta encontrar a data de emissão específica na seção "Informações gerais da Nota"
        # Procurando por padrões específicos de emissão perto de texto relevante
        text = soup.get_text(" ", strip=True)
        
        # Procura pela expressão específica "Emissão:" após termos como "Número:", "Série:", etc.
        # que indica a data de emissão da nota fiscal
        emission_pattern = r'(?:Número:\s*\d+.*?Série:\s*\d+|Série:\s*\d+.*?Número:\s*\d+)?(?:\s*Emiss[aã]o\s*:\s*|\s*EMISS[AÃ]O\s+NORMAL[^<]*?<br[^>]*>.*?Emiss[aã]o\s*:\s*)(\d{2}/\d{2}/\d{4})'
        emission_matches = re.findall(emission_pattern, text, re.IGNORECASE | re.DOTALL)
        if emission_matches:
            for match in emission_matches:
                try:
                    day, month, year = map(int, match.split('/'))
                    return date(year, month, day)
                except ValueError:
                    continue
        
        # Procura por padrões mais específicos na estrutura HTML conhecida
        # Busca dentro de listas ou elementos que contenham informações da nota
        emission_elements = soup.find_all(string=re.compile(r'Emiss[aã]o:', re.IGNORECASE))
        for element in emission_elements:
            # Procura pela data após "Emissão:"
            parent = element.parent if element.parent else None
            if parent:
                # Obtém o texto do pai e procura por padrões de data
                parent_text = parent.get_text(" ", strip=True)
                date_match = re.search(r'Emiss[aã]o\s*:\s*(\d{2}/\d{2}/\d{4})', parent_text, re.IGNORECASE)
                if date_match:
                    date_str = date_match.group(1)
                    try:
                        day, month, year = map(int, date_str.split('/'))
                        return date(year, month, day)
                    except ValueError:
                        continue
        
        # Procura pelo padrão "Emissão: DD/MM/YYYY HH:MM:SS[timezone_offset]"
        # ou variações como "EMISSÃO: DD/MM/YYYY HH:MM:SS" etc.
        date_patterns = [
            r'Emiss[aã]o\s*:\s*(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}(?:[-+]\d{2}:?\d{2})?)',
            r'Data\s+Emiss[aã]o\s*:\s*(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}(?:[-+]\d{2}:?\d{2})?)',
            r'(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}(?:[-+]\d{2}:?\d{2})?)'
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Extrai somente a parte da data (DD/MM/YYYY) ignorando hora e timezone
                date_part = match.split()[0]
                try:
                    day, month, year = map(int, date_part.split('/'))
                    return date(year, month, day)
                except ValueError:
                    continue
        
        # Se não encontrar, tenta encontrar padrões de data isolados (DD/MM/YYYY)
        simple_date_pattern = r'\b(\d{2}/\d{2}/\d{4})\b'
        simple_matches = re.findall(simple_date_pattern, text)
        for match in simple_matches:
            try:
                day, month, year = map(int, match.split('/'))
                return date(year, month, day)
            except ValueError:
                continue
        
        # Se ainda não encontrar, usa data de hoje como fallback
        return date.today()

    def _extract_items(self, soup: BeautifulSoup) -> List[ParsedItem]:
        items: List[ParsedItem] = []

        # Primeiro tenta encontrar a tabela específica de itens com ID "tabResult"
        # que é usada no layout SEFAZ-RJ conforme o HTML fornecido
        table = soup.find("table", {"id": "tabResult"})
        
        if table:
            # Processa a tabela específica de itens
            rows = table.find_all("tr")
            for row in rows:
                # Verifica se é uma linha de item (tem ID começando com "Item + ")
                row_id = row.get("id", "")
                if row_id and row_id.startswith("Item + "):
                    # Extrai os dados do item
                    tds = row.find_all("td")
                    if len(tds) >= 2:
                        # Primeira célula contém nome, código, quantidade, unidade e preço unitário
                        first_td = tds[0]
                        
                        # Extrai o nome do produto (texto com classe "txtTit")
                        name_element = first_td.find("span", class_="txtTit")
                        if name_element:
                            name = name_element.get_text(strip=True)
                            
                            # Log if the name is "NITEROI" to help debug the issue
                            if name.lower() == "niteroi":
                                logger.warning(f"[fiscal-items] Item encontrado com nome 'NITEROI'. Conteúdo completo do first_td: {first_td}")
                                logger.warning(f"[fiscal-items] Texto do elemento txtTit: {name}")
                                
                        else:
                            # Se não encontrar com span txtTit, tenta extrair o primeiro texto significativo
                            # que não seja parte dos spans com informações adicionais
                            all_text = first_td.get_text(separator='|', strip=True)
                            # Divide pelo separador e pega a primeira parte que parece ser o nome do produto
                            parts = all_text.split('|')
                            # Filtra partes vazias e busca a que parece ser o nome do produto
                            for part in parts:
                                part = part.strip()
                                # Ignora partes que contêm códigos, quantidades ou preços
                                if part and not any(keyword in part.lower() for keyword in ['código', 'qtde', 'un:', 'vl. unit', 'r$', 'valor']) and len(part) > 3:
                                    # Certifique-se de que não é um texto irrelevante como "NITEROI"
                                    if part.lower() != "niteroi":
                                        name = part
                                        break
                            else:
                                name = ""
                                
                        # Se ainda assim o nome for "NITEROI", tenta obter de forma mais específica
                        if name.lower() == "niteroi" or not name:
                            # Tenta encontrar o nome do produto olhando apenas para os textos dentro do td
                            # excluindo explicitamente spans com outras informações
                            direct_children_texts = []
                            for child in first_td.children:
                                if hasattr(child, 'name') and child.name not in ['span']:
                                    # Child is a NavigableString, get its text
                                    if child is not None:
                                        # Get the text content of the child and strip it
                                        child_text = str(child).strip()
                                        if child_text:
                                            direct_children_texts.append(child_text)
                                elif hasattr(child, 'name') and child.name == 'span':
                                    # Verifica se é um span com nome do produto (txtTit) ou outro tipo
                                    if 'txtTit' in child.get('class', []) and child.get_text(strip=True).lower() != 'niteroi':
                                        name = child.get_text(strip=True)
                                        break
                                    
                            if not name and direct_children_texts:
                                # Usa o primeiro texto direto que não seja "NITEROI"
                                for text in direct_children_texts:
                                    if text.lower() != 'niteroi':
                                        name = text
                                        break
                        
                        # Extrai quantidade e unidade dos spans
                        qty_text = "0"
                        unit_text = "UN"
                        
                        qtd_span = first_td.find("span", class_="Rqtd")
                        if qtd_span:
                            qtd_str = qtd_span.get_text(strip=True)
                            # Extrai número após "Qtde.:" ou "Qtde:"
                            import re
                            qty_match = re.search(r'Qtde\.?:?\s*([0-9,.]+)', qtd_str, re.IGNORECASE)
                            if qty_match:
                                qty_text = qty_match.group(1)
                        
                        un_span = first_td.find("span", class_="RUN")
                        if un_span:
                            un_str = un_span.get_text(strip=True)
                            # Extrai unidade após "UN: "
                            un_match = re.search(r'UN:\s*(\w+)', un_str, re.IGNORECASE)
                            if un_match:
                                unit_text = un_match.group(1)
                        
                        # Extrai preço unitário
                        unit_price_text = "0"
                        price_span = first_td.find("span", class_="RvlUnit")
                        if price_span:
                            price_str = price_span.get_text(strip=True)
                            # Extrai número após "Vl. Unit.:" ou similar
                            price_match = re.search(r'Vl\.?\s*Unit\.?:?\s*([0-9,.]+)', price_str, re.IGNORECASE)
                            if price_match:
                                unit_price_text = price_match.group(1)
                        
                        # Segunda célula contém o valor total
                        total_cell = tds[1].find("span", class_="valor") if len(tds) > 1 else None
                        total_price_text = total_cell.get_text(strip=True) if total_cell else unit_price_text

                        def _to_float(value: str) -> float:
                            return float(value.replace(".", "").replace(",", "."))

                        try:
                            quantity = _to_float(qty_text)
                        except ValueError:
                            quantity = 0.0
                        try:
                            unit_price = _to_float(unit_price_text)
                        except ValueError:
                            unit_price = 0.0
                        try:
                            total_price = _to_float(total_price_text)
                        except ValueError:
                            total_price = unit_price * quantity

                        if name and name.lower() != "niteroi":  # Filtra o item incorreto "NITERÓI"
                            items.append(
                                ParsedItem(
                                    name=name,
                                    quantity=quantity,
                                    unit=unit_text,
                                    unit_price=unit_price,
                                    total_price=total_price,
                                )
                            )
        else:
            # Fallback: estratégia genérica para outros layouts
            for table in soup.find_all("table"):
                rows = table.find_all("tr")
                if len(rows) < 2:
                    continue
                header_cols = rows[0].find_all(["th", "td"])
                if len(header_cols) < 3:
                    continue

                # Considera que as demais linhas representam itens.
                for row in rows[1:]:
                    cols = row.find_all("td")
                    if len(cols) < 3:
                        continue
                    name = cols[0].get_text(strip=True)
                    
                    # Adiciona filtro para evitar pegar o nome da cidade como item
                    if name.lower() == "niteroi":
                        continue
                        
                    qty_text = cols[1].get_text(strip=True) or "0"
                    unit_text = cols[2].get_text(strip=True)
                    unit_price_text = (
                        cols[3].get_text(strip=True) if len(cols) > 3 else "0"
                    )
                    total_price_text = (
                        cols[4].get_text(strip=True) if len(cols) > 4 else unit_price_text
                    )

                    def _to_float(value: str) -> float:
                        return float(value.replace(".", "").replace(",", "."))

                    try:
                        quantity = _to_float(qty_text)
                    except ValueError:
                        quantity = 0.0
                    try:
                        unit_price = _to_float(unit_price_text)
                    except ValueError:
                        unit_price = 0.0
                    try:
                        total_price = _to_float(total_price_text)
                    except ValueError:
                        total_price = unit_price * quantity

                    if not name:
                        continue

                    items.append(
                        ParsedItem(
                            name=name,
                            quantity=quantity,
                            unit=unit_text,
                            unit_price=unit_price,
                            total_price=total_price,
                        )
                    )

                if items:
                    break

        if not items:
            raise ValueError("Não foi possível localizar itens da nota na página HTML.")

        return items


class RJSefazNFCeAdapter(BaseSefazAdapter):
    """Adapter específico para o layout moderno de NFC-e do RJ.

    O layout não usa tabela tradicional; cada item aparece como um bloco com
    texto semelhante a:

        TAXA ENTREGA CAMBOIN (Código: 6378 )
        Qtde:1   UN: UN   Vl. Unit.: 7,99   Vl. Total 7,99
    """

    ITEM_PATTERN = re.compile(
        r"^(?P<name>.+?)\s+Qtde:(?P<qty>[\d.,]+).*?Vl\. Unit\.:\s*(?P<unit_price>[\d.,]+).*?Vl\. Total\s*(?P<total_price>[\d.,]+)",
        re.IGNORECASE,
    )

    def parse(self, html: str) -> ParsedNote:
        soup = BeautifulSoup(html, "html.parser")

        seller_name = self._extract_seller_name(soup)
        total_amount = self._extract_total_amount(soup)
        emission_date = self._extract_date(soup)
        items = self._extract_items(soup)

        access_key = self._extract_access_key(soup)

        return ParsedNote(
            date=emission_date,
            seller_name=seller_name,
            total_amount=total_amount,
            access_key=access_key,
            items=items,
        )

    def _extract_seller_name(self, soup: BeautifulSoup) -> str:
        # Procura pelo elemento txtTopo com id u20 que contém o nome do vendedor (formato padrão)
        seller_div = soup.find("div", {"class": "txtTopo", "id": "u20"})
        if seller_div:
            seller_name = seller_div.get_text(strip=True)
            logger.info(f"[fiscal-items] seller_name lido: {seller_name}")
            
            # Procura pelo CNPJ que está na div seguinte
            cnpj_div = seller_div.find_next_sibling("div", class_="text")
            if cnpj_div:
                cnpj_text = cnpj_div.get_text(strip=True)
                if "CNPJ:" in cnpj_text.upper():
                    return f"{seller_name}; {cnpj_text}"
            
            return seller_name
        
        # Se não encontrar o formato específico, tenta métodos alternativos (como no RJ)
        # No layout recente, o nome do mercado fica num bloco grande no topo.
        # Estratégia: pegar o primeiro bloco em destaque após o logo.
        candidates = []
        for tag_name in ("h1", "h2", "strong", "div"):
            for el in soup.find_all(tag_name):
                text = el.get_text(strip=True)
                if not text:
                    continue
                if "cnpj:" in text.lower():
                    # Elemento que contém nome + CNPJ; o nome geralmente é o primeiro pedaço.
                    candidates.append(text.split("CNPJ")[0].strip(" :-"))
        if candidates:
            return candidates[0]
        return "Estabelecimento Desconhecido"

    def _extract_access_key(self, soup: BeautifulSoup) -> str:
        # First, try to find the access key using specific HTML elements
        # Look for elements near "Chave de acesso" text
        import re
        
        # Look for span elements with class 'chave' which often contain the access key
        chave_spans = soup.find_all('span', class_='chave')
        if chave_spans:
            raw_key = chave_spans[0].get_text(strip=True)
            # Clean up the key (remove spaces, check if it's 44 digits)
            clean_key = re.sub(r'\s+', '', raw_key)
            if len(clean_key) == 44 and clean_key.isdigit():
                # Format the key nicely with spaces every 4 digits
                formatted_key = ' '.join([clean_key[i:i+4] for i in range(0, len(clean_key), 4)])
                return formatted_key
        
        # Also look for strong tags that might contain "Chave de acesso" followed by the key
        strong_tags = soup.find_all('strong')
        for tag in strong_tags:
            if 'chave de acesso' in tag.get_text(strip=True).lower():
                # Look for the next sibling that might contain the key
                next_sibling = tag.next_sibling
                while next_sibling and len(next_sibling.strip()) == 0:
                    next_sibling = next_sibling.next_sibling
                if next_sibling and isinstance(next_sibling, str):
                    # Extract potential key from the text following the "Chave de acesso" tag
                    potential_key = next_sibling.strip()
                    # Clean up the key
                    clean_key = re.sub(r'[^\d\s]', '', potential_key)  # Keep only digits and spaces
                    clean_key = re.sub(r'\s+', '', clean_key)  # Remove all spaces temporarily
                    if len(clean_key) == 44 and clean_key.isdigit():
                        # Format the key nicely with spaces every 4 digits
                        formatted_key = ' '.join([clean_key[i:i+4] for i in range(0, len(clean_key), 4)])
                        return formatted_key
                
                # Also check parent's siblings
                parent = tag.parent
                if parent:
                    # Look for spans or other elements within the parent that might contain the key
                    for child in parent.children:
                        if child != tag and hasattr(child, 'get_text'):
                            child_text = child.get_text(strip=True)
                            if child_text and len(child_text) >= 44:
                                # Clean up the key
                                clean_key = re.sub(r'\s+', '', child_text)
                                if len(clean_key) == 44 and clean_key.isdigit():
                                    # Format the key nicely with spaces every 4 digits
                                    formatted_key = ' '.join([clean_key[i:i+4] for i in range(0, len(clean_key), 4)])
                                    return formatted_key
        
        # If the specific element approach didn't work, fall back to the original text-based approach
        text = soup.get_text(" ", strip=True)
        
        # Procura por padrões de chave de acesso (44 dígitos)
        # Procura por padrões com espaços ou sem espaços (ex: 3326 0210 6976 9700 0660 6510 7000 3680 6612 6649 4182 ou 33260210697697000660651070003680661266494182)
        patterns = [
            r'Chave\s*de\s*Acesso[^\d]*([0-9\s]{40,50})',  # "Chave de Acesso" followed by digits/spaces
            r'Chave\s*de\s*acesso[^\d]*([0-9\s]{40,50})',  # "Chave de acesso" followed by digits/spaces
            r'([0-9\s]{40,50})',  # Just the 44 digits pattern (with possible spaces)
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Clean up the matched string to keep only digits and remove extra spaces
                clean_match = re.sub(r'\s+', '', match.strip())
                if len(clean_match) == 44 and clean_match.isdigit():
                    # Format the key nicely with spaces every 4 digits
                    formatted_key = ' '.join([clean_match[i:i+4] for i in range(0, len(clean_match), 4)])
                    return formatted_key
        
        # If no key found, generate a UUID-based key as fallback
        return f"SCRAPING-RJ-{uuid4().hex}"

    def _extract_total_amount(self, soup: BeautifulSoup) -> float:
        text = soup.get_text(" ", strip=True)
        # Exemplo de trecho: "Valor a pagar R$: 102,80"
        match = re.search(
            r"Valor\s+a\s+pagar\s*R\$[: ]\s*([\d\.,]+)", text, flags=re.IGNORECASE
        )
        if not match:
            return 0.0
        value_str = match.group(1).replace(".", "").replace(",", ".")
        try:
            return float(value_str)
        except ValueError:
            return 0.0

    def _extract_date(self, soup: BeautifulSoup) -> date:
        # Procura por padrões de data e hora no HTML, como no exemplo:
        # "Emissão: 11/02/2026 07:35:22-03:00"
        import re
        
        # Primeiro tenta encontrar a data de emissão específica na seção "Informações gerais da Nota"
        # Procurando por padrões específicos de emissão perto de texto relevante
        text = soup.get_text(" ", strip=True)
        
        # Procura pela expressão específica "Emissão:" após termos como "Número:", "Série:", etc.
        # que indica a data de emissão da nota fiscal
        emission_pattern = r'(?:Número:\s*\d+.*?Série:\s*\d+|Série:\s*\d+.*?Número:\s*\d+)?(?:\s*Emiss[aã]o\s*:\s*|\s*EMISS[AÃ]O\s+NORMAL[^<]*?<br[^>]*>.*?Emiss[aã]o\s*:\s*)(\d{2}/\d{2}/\d{4})'
        emission_matches = re.findall(emission_pattern, text, re.IGNORECASE | re.DOTALL)
        if emission_matches:
            for match in emission_matches:
                try:
                    day, month, year = map(int, match.split('/'))
                    return date(year, month, day)
                except ValueError:
                    continue
        
        # Procura por padrões mais específicos na estrutura HTML conhecida
        # Busca dentro de listas ou elementos que contenham informações da nota
        emission_elements = soup.find_all(string=re.compile(r'Emiss[aã]o:', re.IGNORECASE))
        for element in emission_elements:
            # Procura pela data após "Emissão:"
            parent = element.parent if element.parent else None
            if parent:
                # Obtém o texto do pai e procura por padrões de data
                parent_text = parent.get_text(" ", strip=True)
                date_match = re.search(r'Emiss[aã]o\s*:\s*(\d{2}/\d{2}/\d{4})', parent_text, re.IGNORECASE)
                if date_match:
                    date_str = date_match.group(1)
                    try:
                        day, month, year = map(int, date_str.split('/'))
                        return date(year, month, day)
                    except ValueError:
                        continue
        
        # Procura pelo padrão "Emissão: DD/MM/YYYY HH:MM:SS[timezone_offset]"
        # ou variações como "EMISSÃO: DD/MM/YYYY HH:MM:SS" etc.
        date_patterns = [
            r'Emiss[aã]o\s*:\s*(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}(?:[-+]\d{2}:?\d{2})?)',
            r'Data\s+Emiss[aã]o\s*:\s*(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}(?:[-+]\d{2}:?\d{2})?)',
            r'(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}(?:[-+]\d{2}:?\d{2})?)'
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Extrai somente a parte da data (DD/MM/YYYY) ignorando hora e timezone
                date_part = match.split()[0]
                try:
                    day, month, year = map(int, date_part.split('/'))
                    return date(year, month, day)
                except ValueError:
                    continue
        
        # Se não encontrar, tenta encontrar padrões de data isolados (DD/MM/YYYY)
        simple_date_pattern = r'\b(\d{2}/\d{2}/\d{4})\b'
        simple_matches = re.findall(simple_date_pattern, text)
        for match in simple_matches:
            try:
                day, month, year = map(int, match.split('/'))
                return date(year, month, day)
            except ValueError:
                continue
        
        # Se ainda não encontrar, usa data de hoje como fallback
        return date.today()

    def _extract_items(self, soup: BeautifulSoup) -> List[ParsedItem]:
        items: List[ParsedItem] = []

        # Estratégia baseada em texto global: no layout do RJ, os dados estão
        # organizados em linhas separadas sequenciais
        full_text = soup.get_text("\n", strip=True)
        print("[RJ-Adapter] Texto completo (primeiras 500 chars):")
        print(full_text[:500])
        lines = [ln.strip() for ln in full_text.splitlines() if ln.strip()]
        print(f"[RJ-Adapter] Total de linhas: {len(lines)}")

        def _to_float(value: str) -> float:
            return float(value.replace(".", "").replace(",", "."))

        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Procura por linhas que contêm "Qtde.:" ou "Qtde:"
            if re.match(r"Qtde\.?:", line, re.IGNORECASE):
                print(f"[RJ-Adapter] Encontrado início de item na linha #{i}: {line}")
                
                # Tenta extrair os dados das próximas linhas
                try:
                    # Linha atual pode ter "Qtde.:" ou só o valor na próxima
                    if ":" in line and len(line) > 6:
                        # Formato: "Qtde.: 1" ou "Qtde.:1"
                        qty_text = line.split(":", 1)[1].strip()
                        next_line_offset = 1
                    else:
                        # Formato: linha com "Qtde.:" e valor na próxima linha
                        qty_text = lines[i + 1] if i + 1 < len(lines) else "0"
                        next_line_offset = 2
                    
                    # Busca UN:, Vl. Unit.:, Vl. Total nas próximas linhas
                    unit = ""
                    unit_price = 0.0
                    total_price = 0.0
                    name = ""
                    
                    # Nome do produto: algumas linhas antes (ignora códigos e linhas especiais)
                    for j in range(max(0, i - 8), i):
                        candidate = lines[j]
                        # Ignora linhas com "Código:", "Clear text", números puros, etc.
                        if candidate and len(candidate) > 3:
                            # Pula linhas que são apenas números (códigos)
                            if candidate.isdigit():
                                continue
                            # Pula linhas especiais
                            if any(x in candidate for x in ["Código", "Clear text", "(Código"]):
                                continue
                            # Pula linhas com palavras-chave de campos
                            if any(x in candidate.lower() for x in ["qtde", "vl.", "un:", "cnpj", "documento auxiliar", ")"]):
                                continue
                            # Aceita apenas se tem letras (não só números e símbolos)
                            if any(c.isalpha() for c in candidate):
                                name = candidate
                                break
                    
                    # Procura os outros campos nas próximas 10 linhas
                    for j in range(i + next_line_offset, min(i + 15, len(lines))):
                        current = lines[j]
                        
                        if re.match(r"UN:", current, re.IGNORECASE):
                            # Próxima linha tem a unidade
                            if j + 1 < len(lines):
                                unit = lines[j + 1]
                        
                        elif re.match(r"Vl\.?\s*Unit\.?:", current, re.IGNORECASE):
                            # Próxima linha tem o preço unitário
                            if j + 1 < len(lines):
                                try:
                                    unit_price = _to_float(lines[j + 1])
                                except:
                                    pass
                        
                        elif re.match(r"Vl\.?\s*Total", current, re.IGNORECASE):
                            # Próxima linha tem o total
                            if j + 1 < len(lines):
                                try:
                                    total_price = _to_float(lines[j + 1])
                                except:
                                    pass
                            break  # Fim dos dados deste item
                    
                    # Converte quantidade
                    try:
                        qty = _to_float(qty_text)
                    except:
                        qty = 0.0
                    
                    if name and qty > 0:
                        print(f"[RJ-Adapter] Item encontrado: {name} - Qtd: {qty}, Unit: {unit}, Preço Unit: {unit_price}, Total: {total_price}")
                        items.append(
                            ParsedItem(
                                name=name,
                                quantity=qty,
                                unit=unit or "UN",
                                unit_price=unit_price,
                                total_price=total_price,
                            )
                        )
                
                except Exception as e:
                    print(f"[RJ-Adapter] Erro ao processar item: {e}")
            
            i += 1

        if not items:
            raise ValueError("Não foi possível localizar itens da NFC-e do RJ no HTML.")

        return items


class ScraperImporter:
    """Fachada para importação de NFC-e via URL com arquitetura de adapters."""

    def __init__(self, backup_file_path: str = "../data/processed_urls_backup.json") -> None:
        # Registro de adapters por "chave" (por exemplo, UF, domínio, etc.).
        # Por enquanto, usamos apenas um adapter padrão.
        self._adapters: Dict[str, Type[BaseSefazAdapter]] = {
            "default": DefaultSefazAdapter,
            "rj_nfe_moderno": RJSefazNFCeAdapter,
        }
        self.backup_file_path = backup_file_path
        self._ensure_backup_directory()
        self._load_processed_urls_from_backup()

    def _ensure_backup_directory(self) -> None:
        """Ensure the backup directory exists."""
        backup_dir = os.path.dirname(self.backup_file_path)
        os.makedirs(backup_dir, exist_ok=True)

    def _load_processed_urls_from_backup(self) -> None:
        """Load processed URLs from backup file."""
        try:
            if os.path.exists(self.backup_file_path):
                with open(self.backup_file_path, 'r', encoding='utf-8') as f:
                    self._processed_urls = set(json.load(f))
            else:
                self._processed_urls = set()
        except Exception:
            # If there's any error reading the backup file, initialize with empty set
            self._processed_urls = set()

    def _save_processed_url_to_backup(self, url: str) -> None:
        """Save a processed URL to the backup file."""
        self._processed_urls.add(url)
        try:
            with open(self.backup_file_path, 'w', encoding='utf-8') as f:
                json.dump(list(self._processed_urls), f, ensure_ascii=False, indent=2)
        except Exception:
            # If we can't save to backup, just continue processing
            pass

    def _select_adapter_key(self, url: str) -> str:
        """Retorna a chave do adapter apropriado para a URL."""

        # Para URLs da SEFAZ-RJ de NFC-e utilizamos um adapter específico.
        if "fazenda.rj.gov.br" in url:
            return "rj_nfe_moderno"

        # Demais casos usam o adapter padrão.
        return "default"

    def import_from_url(
        self,
        url: str,
        *,
        force_browser: bool = False,
    ) -> ParsedNote:
        """Faz o download da página da NFC-e e retorna uma `ParsedNote`."""

        # Modo "auto": tenta requests primeiro (quando não for forçado browser).
        # Se detectar bloqueio/parse inválido, recorre ao browser real (Playwright).
        if not force_browser:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            html_requests = response.text
        else:
            html_requests = ""

        key = self._select_adapter_key(url)
        adapter_cls = self._adapters.get(key, DefaultSefazAdapter)
        adapter = adapter_cls()

        if html_requests:
            # Se já parecer bloqueio no requests, pula direto para browser.
            if not _looks_like_sefaz_block_page(html_requests):
                try:
                    result = adapter.parse(html_requests)
                    # Save URL to backup after successful processing
                    self._save_processed_url_to_backup(url)
                    return result
                except ValueError:
                    pass

        # Browser real
        fetcher = BrowserHTMLFetcher()
        html_browser = fetcher.fetch(url)
        if _looks_like_sefaz_block_page(html_browser):
            raise ValueError(
                "SEFAZ bloqueou o acesso a partir deste IP (mesmo via browser). "
                "Para importar NFC-e RJ, configure um proxy (preferencialmente residencial/rotativo)."
            )
        result = adapter.parse(html_browser)
        # Save URL to backup after successful processing
        self._save_processed_url_to_backup(url)
        return result


__all__ = [
    "ScraperImporter",
    "BaseSefazAdapter",
    "DefaultSefazAdapter",
    "RJSefazNFCeAdapter",
]

