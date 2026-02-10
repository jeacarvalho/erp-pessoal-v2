from __future__ import annotations

from datetime import date
import re
from typing import Dict, List, Type
from uuid import uuid4

import requests
from bs4 import BeautifulSoup

from .xml_handler import ParsedItem, ParsedNote
from .browser_fetcher import BrowserHTMLFetcher


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

        access_key = f"SCRAPING-{uuid4().hex}"

        return ParsedNote(
            date=emission_date,
            seller_name=seller_name,
            total_amount=total_amount,
            access_key=access_key,
            items=items,
        )

    def _extract_seller_name(self, soup: BeautifulSoup) -> str:
        # Heurística simples: primeiro <h1> ou <h2>.
        for tag_name in ("h1", "h2"):
            tag = soup.find(tag_name)
            if tag and tag.get_text(strip=True):
                return tag.get_text(strip=True)
        return "Estabelecimento Desconhecido"

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
        # Heurística mínima: se não conseguir extrair, usa data de hoje.
        # Em produção, parsear datas com regex em cima do texto.
        return date.today()

    def _extract_items(self, soup: BeautifulSoup) -> List[ParsedItem]:
        items: List[ParsedItem] = []

        # Estratégia genérica: pega a primeira tabela com pelo menos 3 colunas.
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

        access_key = f"SCRAPING-RJ-{uuid4().hex}"

        return ParsedNote(
            date=emission_date,
            seller_name=seller_name,
            total_amount=total_amount,
            access_key=access_key,
            items=items,
        )

    def _extract_seller_name(self, soup: BeautifulSoup) -> str:
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
        # No RJ, a data costuma aparecer próxima ao topo; como heurística simples
        # mantemos a mesma estratégia do adapter padrão (data de hoje).
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

    def __init__(self) -> None:
        # Registro de adapters por "chave" (por exemplo, UF, domínio, etc.).
        # Por enquanto, usamos apenas um adapter padrão.
        self._adapters: Dict[str, Type[BaseSefazAdapter]] = {
            "default": DefaultSefazAdapter,
            "rj_nfe_moderno": RJSefazNFCeAdapter,
        }

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
                    return adapter.parse(html_requests)
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
        return adapter.parse(html_browser)


__all__ = [
    "ScraperImporter",
    "BaseSefazAdapter",
    "DefaultSefazAdapter",
    "RJSefazNFCeAdapter",
]

