# Implementação da Lógica de Captura de Dados de Consumo

## ✅ Componentes Implementados

### 1. **Parser de XML (Federal)** - `backend/app/services/xml_handler.py`

**Classe:** `XMLProcessor`
- Utiliza `xml.etree.ElementTree` para parsing de NF-e/NFC-e
- **Extrai:**
  - Data de emissão (dhEmi/dEmi)
  - Nome do estabelecimento (emit/xNome)
  - Valor total (total/ICMSTot/vNF)
  - Chave de acesso (chNFe ou atributo Id)
  - Lista de itens com: Nome, Quantidade, Unidade, Preço Unitário, Preço Total

**Método principal:** `parse(xml_content: str | bytes) -> ParsedNote`

---

### 2. **Scraper de NFC-e (Estadual)** - `backend/app/services/scraper_handler.py`

**Arquitetura de Adapters:**

- **`BaseSefazAdapter`**: Interface base para adapters
- **`DefaultSefazAdapter`**: Adapter genérico para layouts comuns
- **`RJSefazNFCeAdapter`**: Adapter especializado para SEFAZ-RJ
- **`ScraperImporter`**: Fachada que seleciona o adapter apropriado por URL

**Recursos:**
- Suporte para requisições HTTP simples (requests)
- Fallback para browser real (Playwright) quando detectado bloqueio
- Sistema extensível: novos adapters podem ser facilmente adicionados

**Método principal:** `import_from_url(url: str, force_browser: bool) -> ParsedNote`

---

### 3. **Browser Fetcher** - `backend/app/services/browser_fetcher.py`

**Classe:** `BrowserHTMLFetcher`
- Utiliza Playwright para contornar bloqueios de scrapers básicos
- Configurável (headless, timeout, user-agent, etc.)
- Lazy import do Playwright (não quebra se não instalado)

---

### 4. **Endpoints de Importação** - `backend/app/main.py`

#### **POST /import/xml**
```python
# Recebe arquivo XML via upload
# Retorna: note_id, items_count, seller_name, total_amount
```

#### **POST /import/url**
```python
# Payload: { "url": "...", "use_browser": false }
# Retorna: note_id, items_count, seller_name, total_amount
```

---

### 5. **Lógica de Persistência**

**Função:** `_persist_parsed_note(parsed: ParsedNote, source_type: FiscalSourceType, db: Session)`

- Cria registro na tabela `fiscal_notes`
- Cria registros associados na tabela `fiscal_items`
- Garante integridade referencial automática via SQLAlchemy

**Models utilizados:**
- `FiscalNote`: Cabeçalho da nota (data, valor total, emissor, chave, tipo de fonte)
- `FiscalItem`: Itens individuais (produto, quantidade, preço unitário, preço total)

---

### 6. **Testes Unitários** - `backend/tests/test_import.py`

**Teste:** `test_xml_processor_parses_quantity_and_unit_price_separately()`

- Valida parsing de XML mockado
- Garante separação correta entre quantidade e preço unitário
- **Status:** ✅ PASSANDO

---

## 📋 Dependências (requirements.txt)

```
fastapi==0.128.7
uvicorn
sqlalchemy==2.0.46
pydantic
pytest
requests          # Para requisições HTTP básicas
beautifulsoup4    # Para parsing HTML
lxml              # Para parsing XML otimizado
playwright        # Para browser real (bypass de bloqueios)
```

---

## 🚀 Como Usar

### Importar via XML:
```bash
curl -X POST http://localhost:8000/import/xml \
  -F "file=@nota.xml"
```

### Importar via URL:
```bash
curl -X POST http://localhost:8000/import/url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.fazenda.rj.gov.br/nfce/consulta?p=...", "use_browser": false}'
```

### Executar Testes:
```bash
python3 -m pytest backend/tests/test_import.py -v
```

---

## 🎯 Arquitetura de Adapters

A arquitetura permite adicionar facilmente suporte para diferentes layouts de SEFAZ:

```python
class NovoEstadoAdapter(BaseSefazAdapter):
    def parse(self, html: str) -> ParsedNote:
        # Implementação específica para o estado
        ...
```

Registrar o adapter em `ScraperImporter`:
```python
self._adapters["novo_estado"] = NovoEstadoAdapter
```

Atualizar `_select_adapter_key()` para detectar a URL do estado:
```python
if "sefaz.estado.gov.br" in url:
    return "novo_estado"
```

---

## ✅ Status da Implementação

- [x] Parser XML com xml.etree.ElementTree
- [x] Scraper com BeautifulSoup4
- [x] Arquitetura de adapters extensível
- [x] Endpoints REST para importação
- [x] Persistência em fiscal_notes e fiscal_items
- [x] Testes unitários validados
- [x] Suporte a browser real (Playwright)
- [x] Adapter específico para SEFAZ-RJ

**Todas as funcionalidades solicitadas foram implementadas com sucesso!**
