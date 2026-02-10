# 🖥️ Guia Rápido - Frontend Flet

## 🎯 Como Executar

### Opção 1: Script Automático (Recomendado)
```bash
./run_web.sh
```

### Opção 2: Manual
```bash
cd web
pip install -r requirements.txt
python -m app.main
```

## 📱 Funcionalidades Implementadas

### ✅ 1. NavigationRail
- Menu lateral com 4 opções
- Navegação entre: Dashboard, Lançamentos, Categorias e Importar

### ✅ 2. Tela de Importação
**Importar por URL:**
- Campo de texto para colar URL da NFC-e
- Checkbox para forçar uso de navegador
- Botão "Importar da URL" com feedback visual
- SnackBar de sucesso/erro

**Importar por XML:**
- FilePicker para selecionar arquivo .xml
- Upload direto para o backend
- SnackBar de confirmação

**Tabela de Itens:**
- Mostra os últimos 20 itens importados
- Colunas: Produto, Quantidade, Preço Unit., Total, Data/Vendedor
- Atualiza automaticamente após importação

### ✅ 3. Dashboard de Gastos
**PieChart:**
- Visualização de gastos por categoria
- Cores automáticas para cada categoria
- Valores em R$ nas fatias

**Filtros de Data:**
- Campo "Data Início" (padrão: primeiro dia do mês)
- Campo "Data Fim" (padrão: hoje)
- Botão "Atualizar Dashboard"

**Funcionalidade:**
- Busca transações do backend
- Filtra por período
- Agrupa gastos (valores negativos) por categoria
- Exibe mensagem se não houver dados

### ✅ 4. Outras Telas

**Lançamentos:**
- Tabela de transações bancárias
- ID, Data, Descrição, Valor (colorido), Categoria
- Verde para receitas, vermelho para despesas

**Categorias:**
- Lista em cards
- Mostra ID, Nome e Categoria Pai
- Ícones visuais

## 🔌 Endpoints Utilizados

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/categories` | Lista categorias |
| GET | `/transactions` | Lista transações |
| GET | `/fiscal-items?limit=20` | Lista itens fiscais |
| POST | `/import/url` | Importa nota por URL |
| POST | `/import/xml` | Importa nota por XML |

## 🎨 Características Técnicas

- **Framework**: Flet 0.21+
- **HTTP Client**: httpx
- **Arquitetura**: Classe única `ERPApp` com métodos para cada view
- **Gerenciamento de Estado**: Variáveis de instância
- **Feedback**: SnackBars para sucesso/erro
- **Responsivo**: Expande para preencher a janela

## 🧪 Testando o Frontend

### 1. Certifique-se de que o backend está rodando:
```bash
cd backend
uvicorn app.main:app --reload
```

Deve exibir: `Uvicorn running on http://localhost:8000`

### 2. Execute o frontend:
```bash
./run_web.sh
```

### 3. Teste as funcionalidades:

**Dashboard:**
1. Abra a tela "Dashboard" (já é a padrão)
2. Ajuste as datas se necessário
3. Clique em "Atualizar Dashboard"
4. Observe o gráfico de pizza (se houver transações com categorias)

**Lançamentos:**
1. Clique em "Lançamentos"
2. Veja a lista de transações

**Categorias:**
1. Clique em "Categorias"
2. Veja os cards de categorias

**Importar:**
1. Clique em "Importar"
2. **Teste URL**: Cole uma URL de NFC-e válida e clique "Importar da URL"
3. **Teste XML**: Clique "Selecionar arquivo XML", escolha um arquivo e aguarde
4. Observe o SnackBar de sucesso
5. Veja a tabela "Últimos Itens Importados" se atualizar

## 🐛 Troubleshooting

### Erro: "Connection refused"
**Causa**: Backend não está rodando
**Solução**: 
```bash
cd backend && uvicorn app.main:app --reload
```

### Erro: "ModuleNotFoundError: No module named 'flet'"
**Causa**: Dependências não instaladas
**Solução**:
```bash
cd web && pip install -r requirements.txt
```

### Gráfico vazio no Dashboard
**Causa**: Não há transações com categorias ou nenhuma despesa
**Solução**: Crie algumas transações com valores negativos e categorias associadas

### Tabela de itens vazia
**Causa**: Nenhuma nota fiscal foi importada ainda
**Solução**: Use a aba "Importar" para adicionar notas

## 📊 Exemplo de Fluxo Completo

1. **Inicie o Backend**
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

2. **Inicie o Frontend**
   ```bash
   ./run_web.sh
   ```

3. **Importe uma Nota Fiscal**
   - Vá para "Importar"
   - Cole uma URL de NFC-e
   - Clique "Importar da URL"
   - Veja o SnackBar de sucesso
   - Observe a tabela de itens atualizar

4. **Visualize no Dashboard**
   - Vá para "Dashboard"
   - (Ainda não haverá dados aqui até criar transações associadas)

5. **Veja as Categorias**
   - Vá para "Categorias"
   - Veja as categorias padrão do sistema

## 🎯 Estrutura do Código

```python
class ERPApp:
    - __init__(): Inicializa a aplicação
    - setup_ui(): Cria NavigationRail e layout
    - on_navigation_change(): Troca de tela
    - build_dashboard_view(): Dashboard com PieChart
    - build_lancamentos_view(): Tabela de transações
    - build_categorias_view(): Lista de categorias
    - build_importar_view(): Tela de importação
    - refresh_fiscal_items_table(): Atualiza itens
    - show_snackbar(): Exibe mensagens
    - cleanup(): Fecha recursos
```

## ✨ Melhorias Futuras Sugeridas

- [ ] Adicionar modo escuro/claro
- [ ] Implementar paginação nas tabelas
- [ ] Adicionar busca/filtros avançados
- [ ] Edição inline de transações
- [ ] Exportação de relatórios (PDF, Excel)
- [ ] Gráficos adicionais (linhas, barras)
- [ ] Associação automática de itens a categorias
- [ ] Notificações/alertas personalizados
- [ ] Atalhos de teclado
- [ ] Tema personalizado

## 🎉 Pronto!

O frontend está totalmente funcional e integrado ao backend. Experimente todas as funcionalidades e aproveite o sistema!
