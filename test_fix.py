#!/usr/bin/env python3
"""
Script temporário para corrigir o método _extract_items no scraper_handler.py
"""

import re

def fix_scraper_handler():
    # Lê o conteúdo do arquivo
    with open('/workspace/backend/app/services/scraper_handler.py', 'r') as f:
        content = f.read()

    # Define o novo método _extract_items
    new_method = '''    def _extract_items(self, soup: BeautifulSoup) -> List[ParsedItem]:
        items: List[ParsedItem] = []

        # Procura especificamente pela tabela de resultados que contém os itens
        # conforme o HTML fornecido no exemplo
        table = soup.find('table', {'id': 'tabResult'})
        
        if table:
            # Processa cada linha da tabela como um item
            rows = table.find_all('tr')
            for row in rows:
                # Verifica se é uma linha de item (tem ID começando com "Item + ")
                row_id = row.get('id', '')
                if row_id.startswith('Item + '):
                    # Extrai informações do item
                    # O nome do produto está em um span com classe txtTit
                    product_span = row.find('span', class_='txtTit')
                    if product_span:
                        # Extrai o nome do produto, removendo possíveis códigos
                        product_text = product_span.get_text(strip=True)
                        # Remove o código do produto se presente (entre parênteses)
                        if '(Código:' in product_text:
                            product_name = product_text.split('(Código:')[0].strip()
                        else:
                            product_name = product_text
                        
                        # Extrai quantidade, unidade e valores
                        qtd_span = row.find('span', class_='Rqtd')
                        un_span = row.find('span', class_='RUN')
                        unit_price_span = row.find('span', class_='RvlUnit')
                        total_price_span = row.find('td', class_='txtTit noWrap')
                        
                        quantity = 0.0
                        unit = "UN"
                        unit_price = 0.0
                        total_price = 0.0
                        
                        # Extrai quantidade
                        if qtd_span:
                            qtd_text = qtd_span.get_text(strip=True)
                            # Extrai o número após "Qtde.:"
                            import re
                            qtd_match = re.search(r'Qtde\.:(.+)', qtd_text)
                            if qtd_match:
                                try:
                                    qty_str = qtd_match.group(1).strip().replace(".", "").replace(",", ".")
                                    quantity = float(qty_str)
                                except:
                                    quantity = 0.0
                        
                        # Extrai unidade
                        if un_span:
                            un_text = un_span.get_text(strip=True)
                            # Extrai o texto após "UN: "
                            un_match = re.search(r'UN:\s*(.+)', un_text)
                            if un_match:
                                unit = un_match.group(1).strip()
                        
                        # Extrai preço unitário
                        if unit_price_span:
                            unit_price_text = unit_price_span.get_text(strip=True)
                            # Extrai o número após "Vl. Unit.:"
                            price_match = re.search(r'Vl\. Unit\.:\\s*([0-9,.]+)', unit_price_text)
                            if price_match:
                                try:
                                    price_str = price_match.group(1).strip().replace(".", "").replace(",", ".")
                                    unit_price = float(price_str)
                                except:
                                    unit_price = 0.0
                        
                        # Extrai preço total
                        if total_price_span:
                            # O valor total está em um span com classe 'valor'
                            valor_span = total_price_span.find('span', class_='valor')
                            if valor_span:
                                try:
                                    total_str = valor_span.get_text(strip=True).replace(".", "").replace(",", ".")
                                    total_price = float(total_str)
                                except:
                                    total_price = 0.0
                        
                        # Só adiciona o item se tiver nome válido
                        if product_name and product_name.strip():
                            items.append(
                                ParsedItem(
                                    name=product_name,
                                    quantity=quantity,
                                    unit=unit,
                                    unit_price=unit_price,
                                    total_price=total_price,
                                )
                            )
        else:
            # Se não encontrar a tabela específica, tenta o método antigo baseado em texto
            # como fallback (mas isso pode causar o problema mencionado)
            full_text = soup.get_text("\\n", strip=True)
            lines = [ln.strip() for ln in full_text.splitlines() if ln.strip()]

            def _to_float(value: str) -> float:
                return float(value.replace(".", "").replace(",", "."))

            i = 0
            while i < len(lines):
                line = lines[i]
                
                # Procura por linhas que contêm "Qtde.:"
                if re.match(r"Qtde\.?:", line, re.IGNORECASE):
                    
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
                            
                            elif re.match(r"Vl\.?\\s*Unit\.?:", current, re.IGNORECASE):
                                # Próxima linha tem o preço unitário
                                if j + 1 < len(lines):
                                    try:
                                        unit_price = _to_float(lines[j + 1])
                                    except:
                                        pass
                            
                            elif re.match(r"Vl\.?\\s*Total", current, re.IGNORECASE):
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
                            items.append(
                                ParsedItem(
                                    name=name,
                                    quantity=qty,
                                    unit=unit or "UN",
                                    unit_price=unit_price,
                                    total_price=total_price,
                                )
                            )
                    except Exception:
                        pass
                
                i += 1

        if not items:
            raise ValueError("Não foi possível localizar itens da NFC-e do RJ no HTML.")

        return items'''

    # Localiza a parte do código que precisa ser substituída
    pattern = r'(\s+)def _extract_items\(self, soup: BeautifulSoup\) -> List\[ParsedItem\]:.*?\n(\s+)(?=def |class |\Z)'
    
    # Substitui o método existente
    updated_content = re.sub(pattern, r'\1' + new_method + r'\n\n\2', content, 1, re.DOTALL)

    # Escreve o conteúdo atualizado de volta ao arquivo
    with open('/workspace/backend/app/services/scraper_handler.py', 'w') as f:
        f.write(updated_content)

    print("Método _extract_items atualizado com sucesso!")

if __name__ == "__main__":
    fix_scraper_handler()