# ERP Pessoal - Frontend Web

Interface gráfica desenvolvida com Flet para o sistema ERP Pessoal.

## 📋 Recursos

- **NavigationRail**: Navegação lateral com 4 seções principais
- **Dashboard de Gastos**: Visualização com PieChart mostrando distribuição por categoria
- **Lançamentos**: Tabela de transações bancárias
- **Categorias**: Lista de categorias cadastradas
- **Importação**: Upload de NFC-e via URL ou arquivo XML

## 🚀 Instalação

### 1. Instalar Dependências

```bash
cd web
pip install -r requirements.txt
```

### 2. Certificar-se de que o Backend está rodando

O backend deve estar operacional em `http://localhost:8000`:

```bash
cd ../backend
uvicorn app.main:app --reload
```

### 3. Executar o Frontend

```bash
cd web
python -m app.main
```

Ou diretamente:

```bash
python web/app/main.py
```

## 🎨 Interface

### Dashboard
- Filtros de data (início e fim)
- Gráfico de pizza mostrando gastos por categoria
- Atualização em tempo real

### Lançamentos
- Tabela com todas as transações
- Valores em verde (receita) e vermelho (despesa)
- Categorias associadas

### Categorias
- Lista de todas as categorias
- Exibição hierárquica (pai/filho)
- Cards visuais organizados

### Importar
**Por URL:**
- Campo de texto para colar URL da NFC-e
- Opção de usar navegador para sites complexos
- Feedback visual com SnackBar

**Por XML:**
- Seletor de arquivo XML
- Suporte para NF-e e NFC-e
- Upload direto para o backend

**Tabela de Itens:**
- Últimos 20 itens importados
- Detalhes: produto, quantidade, preços
- Data e vendedor da nota

## 🔧 Configuração

### Alterar URL do Backend

Edite o arquivo `web/app/main.py`:

```python
# Configuração da URL do backend
BACKEND_URL = "http://localhost:8000"  # Altere aqui se necessário
```

## 📦 Dependências

- **Flet**: Framework para criação de interfaces gráficas
- **httpx**: Cliente HTTP para comunicação com o backend

## 🏗️ Estrutura

```
web/
├── app/
│   └── main.py          # Aplicação principal
├── tests/               # Testes (a implementar)
├── requirements.txt     # Dependências Python
└── README.md           # Este arquivo
```

## 🔄 Integração com Backend

O frontend consome os seguintes endpoints:

- `GET /categories` - Lista categorias
- `GET /transactions` - Lista transações
- `POST /transactions` - Cria transação
- `POST /import/url` - Importa NFC-e por URL
- `POST /import/xml` - Importa NFC-e por arquivo XML
- `GET /fiscal-items` - Lista itens fiscais importados

## 💡 Uso

1. **Iniciar o Backend** em um terminal
2. **Executar o Frontend** em outro terminal
3. **Navegar** pela interface usando o menu lateral
4. **Importar Notas**: Use a aba "Importar" para adicionar notas fiscais
5. **Visualizar Dados**: Dashboard e tabelas são atualizados automaticamente

## 🐛 Troubleshooting

### Erro de Conexão com Backend
```
Erro: Connection refused
```
**Solução**: Verifique se o backend está rodando em `localhost:8000`

### Flet não instalado
```
ModuleNotFoundError: No module named 'flet'
```
**Solução**: Execute `pip install -r requirements.txt`

### Erro ao importar URL
```
Erro ao importar: 422 Unprocessable Entity
```
**Solução**: Verifique se a URL está correta e completa. Tente marcar a opção "Usar navegador"

## 📝 Notas

- O frontend é uma aplicação desktop que roda localmente
- Todas as operações dependem do backend estar operacional
- Os dados são armazenados no banco de dados do backend (SQLite por padrão)
- A interface é responsiva e se adapta ao tamanho da janela

## 🎯 Próximos Passos

- [ ] Adicionar edição de transações
- [ ] Implementar filtros avançados
- [ ] Adicionar exportação de relatórios
- [ ] Implementar temas claro/escuro
- [ ] Adicionar testes automatizados
