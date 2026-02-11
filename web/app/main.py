"""
ERP Pessoal - Frontend com Flet
Interface principal com NavigationRail e integração com backend
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional

import flet as ft
import httpx
import asyncio


# Configuração da URL do backend
BACKEND_URL = "http://127.0.0.1:8000"


class ERPApp:
    """Aplicação principal do ERP Pessoal."""

    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "ERP Pessoal"
        self.page.padding = 0
        self.page.theme_mode = ft.ThemeMode.LIGHT
        
        # Estado da navegação
        self.selected_index = 0
        
        # Componentes principais
        self.navigation_rail: Optional[ft.NavigationRail] = None
        self.content_area: Optional[ft.Container] = None
        
        # Cliente HTTP
        self.http_client = httpx.Client(base_url=BACKEND_URL, timeout=2.0, trust_env=False)
        self.async_http_client = httpx.AsyncClient(base_url=BACKEND_URL, timeout=2.0, trust_env=False)
        
        # Dados em cache
        self.categories: List[Dict[str, Any]] = []
        self.fiscal_items: List[Dict[str, Any]] = []
        
        # Verifica se o backend está disponível antes de iniciar a UI
        print("DEBUG: Verificando saúde do backend...")
        # Mostrar mensagem de carregamento enquanto verifica a saúde do backend
        self.page.add(ft.Text("Carregando..."))
        self.page.update()
        
        if not self.check_backend_health():
            print("ERRO: Backend não está respondendo. Verifique se o servidor está rodando em http://localhost:8000")
            self.page.clean()  # Limpa a mensagem de carregamento
            self.page.add(
                ft.Column([
                    ft.Text("Backend não está disponível!", style="headlineMedium", color="red"),
                    ft.Text(f"Verifique se o servidor está rodando em {BACKEND_URL}/docs", style="bodyLarge"),
                ])
            )
            self.page.update()
        else:
            print("DEBUG: Backend saudável, iniciando UI...")
        self.setup_ui()
        print("DEBUG: setup_ui concluído")

    def check_backend_health(self) -> bool:
        """Verifica se o backend está saudável."""
        try:
            url = f"{BACKEND_URL}/health"
            print(f"DEBUG FRONTEND: Tentando conectar em {url}...")
            response = self.http_client.get("/health")  # Usando o novo endpoint de health check
            print(f"DEBUG: Resposta do backend: status={response.status_code}, content={response.text[:200]}")
            return response.status_code == 200
        except Exception as e:
            print("ERRO: O Backend na porta 8000 não foi encontrado")
            print(f"Detalhes do erro: {e}")
            import traceback
            traceback.print_exc()
            return False

    def setup_ui(self):
        """Configura a interface principal."""
        print("DEBUG: Iniciando setup_ui")
        
        # NavigationRail
        print("DEBUG: Criando NavigationRail")
        
        # Função para sincronização manual
        def manual_sync(e):
            print("DEBUG: Botão de sincronização manual acionado")
            # Atualiza o conteúdo baseado na seleção atual
            if self.selected_index == 0:
                self.content_area.content = self.build_dashboard_view()
            elif self.selected_index == 1:
                self.content_area.content = self.build_lancamentos_view()
            elif self.selected_index == 2:
                self.content_area.content = self.build_categorias_view()
            elif self.selected_index == 3:
                self.content_area.content = self.build_importar_view()
            
            self.page.update()
        
        # Adiciona o botão de refresh ao NavigationRail
        self.navigation_rail = ft.NavigationRail(
            selected_index=self.selected_index,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            destinations=[
                ft.NavigationRailDestination(
                    label="Dashboard",
                ),
                ft.NavigationRailDestination(
                    label="Lançamentos",
                ),
                ft.NavigationRailDestination(
                    label="Categorias",
                ),
                ft.NavigationRailDestination(
                    label="Importar",
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.REFRESH_ROUNDED,
                    selected_icon=ft.icons.REFRESH_ROUNDED,
                    label="Sincronizar",
                ),
            ],
            on_change=self.on_navigation_change_refresh,
        )
        
        # Armazena a função de sincronização para uso no handler
        self.manual_sync = manual_sync
        
        # Área de conteúdo
        print("DEBUG: Criando content_area")
        self.content_area = ft.Container(
            content=self.build_dashboard_view(),
            expand=True,
            padding=20,
        )
        
        # Layout principal
        print("DEBUG: Adicionando layout à página")
        self.page.add(
            ft.Row(
                [
                    self.navigation_rail,
                    ft.VerticalDivider(width=1),
                    self.content_area,
                ],
                expand=True,
            )
        )
        print("DEBUG: Layout adicionado, chamando page.update()")
        self.page.update()
        print("DEBUG: setup_ui completo!")

    def on_navigation_change_refresh(self, e):
        """Manipula mudanças na navegação, incluindo o botão de sincronização."""
        self.selected_index = e.control.selected_index
        
        # Verifica se é o botão de sincronização (último item)
        destinations_count = len(self.navigation_rail.destinations)
        if self.selected_index == destinations_count - 1:  # Índice do botão de sincronização
            print("DEBUG: Botão de sincronização selecionado")
            self.manual_sync(None)
            # Retorna para a última opção válida (antes do botão de sincronização)
            self.selected_index = max(0, destinations_count - 2)
            self.navigation_rail.selected_index = self.selected_index
        else:
            # Atualiza o conteúdo baseado na seleção normal
            if self.selected_index == 0:
                self.content_area.content = self.build_dashboard_view()
            elif self.selected_index == 1:
                self.content_area.content = self.build_lancamentos_view()
            elif self.selected_index == 2:
                self.content_area.content = self.build_categorias_view()
            elif self.selected_index == 3:
                self.content_area.content = self.build_importar_view()
            
            self.page.update()

    def build_dashboard_view(self) -> ft.Column:
        """Constrói a visualização do Dashboard."""
        
        # Seletor de data
        start_date_field = ft.TextField(
            label="Data Início",
            value=datetime.date.today().replace(day=1).isoformat(),
            width=200,
            hint_text="YYYY-MM-DD",
        )
        
        end_date_field = ft.TextField(
            label="Data Fim",
            value=datetime.date.today().isoformat(),
            width=200,
            hint_text="YYYY-MM-DD",
        )
        
        # Placeholder para o gráfico de pizza
        chart_container = ft.Container(
            content=ft.Text("Carregando dados...", size=16),
            alignment=ft.alignment.Alignment(0, 0),
            height=400,
        )
        
        def on_filter_click(e):
            """Atualiza o dashboard com os filtros selecionados."""
            try:
                start = start_date_field.value
                end = end_date_field.value
                
                # Busca transações
                url = f"{BACKEND_URL}/transactions"
                print(f"DEBUG FRONTEND: Tentando conectar em {url}...")
                response = self.http_client.get("/transactions")
                response.raise_for_status()
                transactions = response.json()
                
                # Filtra por data
                filtered = [
                    tx for tx in transactions
                    if start <= tx["date"] <= end
                ]
                
                # Agrupa por categoria
                category_totals: Dict[str, float] = {}
                for tx in filtered:
                    if tx.get("category") and tx["amount"] < 0:  # Apenas gastos
                        cat_name = tx["category"]["name"]
                        category_totals[cat_name] = category_totals.get(cat_name, 0) + abs(tx["amount"])
                
                # Cria o gráfico de pizza
                if category_totals:
                    sections = [
                        ft.PieChartSection(
                            value=value,
                            title=f"{name}\nR$ {value:.2f}",
                            title_style=ft.TextStyle(
                                size=12,
                                color="white",
                                weight=ft.FontWeight.BOLD,
                            ),
                            radius=100,
                        )
                        for name, value in category_totals.items()
                    ]
                    
                    chart_container.content = ft.PieChart(
                        sections=sections,
                        sections_space=2,
                        center_space_radius=40,
                        expand=True,
                    )
                else:
                    chart_container.content = ft.Text(
                        "Nenhum gasto encontrado no período selecionado",
                        size=16,
                    )
                
                self.page.update()
                
            except Exception as ex:
                self.show_snackbar(f"Erro ao carregar dashboard: {str(ex)}", "red")
        
        filter_button = ft.FilledButton(
            "Atualizar Dashboard",
            on_click=on_filter_click,
        )
        
        # Botão para carregar dados iniciais
        def load_initial_data(e):
            """Carrega dados iniciais quando o usuário clica"""
            on_filter_click(None)
            # Desabilita o botão após carregar
            load_data_button.disabled = True
            load_data_button.update()
        
        load_data_button = ft.FilledButton(
            "Carregar Dados",
            on_click=load_initial_data,
        )
        
        return ft.Column(
            [
                ft.Text("Dashboard de Gastos", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Row(
                    [
                        start_date_field,
                        end_date_field,
                        filter_button,
                    ],
                    spacing=10,
                ),
                ft.Row(
                    [
                        load_data_button,
                    ]
                ),
                ft.Container(height=20),
                chart_container,
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def build_lancamentos_view(self) -> ft.Column:
        """Constrói a visualização de Lançamentos (Transações)."""
        
        # Tabela de transações
        transactions_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID")),
                ft.DataColumn(ft.Text("Data")),
                ft.DataColumn(ft.Text("Descrição")),
                ft.DataColumn(ft.Text("Valor")),
                ft.DataColumn(ft.Text("Categoria")),
            ],
            rows=[],
        )
        
        def load_transactions():
            """Carrega as transações do backend."""
            try:
                url = f"{BACKEND_URL}/transactions"
                print(f"DEBUG FRONTEND: Tentando conectar em {url}...")
                response = self.http_client.get("/transactions")
                response.raise_for_status()
                transactions = response.json()
                
                transactions_table.rows = [
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(str(tx["id"]))),
                            ft.DataCell(ft.Text(tx["date"])),
                            ft.DataCell(ft.Text(tx["description"])),
                            ft.DataCell(ft.Text(
                                f"R$ {tx['amount']:.2f}",
                                color="green" if tx["amount"] > 0 else "red",
                            )),
                            ft.DataCell(ft.Text(
                                tx["category"]["name"] if tx.get("category") else "Sem categoria"
                            )),
                        ]
                    )
                    for tx in transactions
                ]
                
                self.page.update()
                
            except Exception as ex:
                self.show_snackbar(f"Erro ao carregar transações: {str(ex)}", "red")
        
        # Botão para carregar dados iniciais
        def load_initial_transactions(e):
            """Carrega dados iniciais quando o usuário clica"""
            load_transactions()
            # Desabilita o botão após carregar
            load_transactions_button.disabled = True
            load_transactions_button.update()
        
        load_transactions_button = ft.FilledButton(
            "Carregar Dados",
            on_click=load_initial_transactions,
        )
        
        return ft.Column(
            [
                ft.Text("Lançamentos Bancários", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Row(
                    [
                        load_transactions_button,
                    ]
                ),
                ft.Container(
                    content=transactions_table,
                    border=ft.border.all(1, "#9e9e9e"),
                    border_radius=5,
                    padding=10,
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def build_categorias_view(self) -> ft.Column:
        """Constrói a visualização de Categorias."""
        
        # Container para o conteúdo
        content_container = ft.Container(expand=True)
        
        async def load_categories():
            """Carrega as categorias do backend."""
            print("Iniciando requisição")
            try:
                # Mostra o indicador de progresso
                content_container.content = ft.Column([
                    ft.ProgressRing(),
                    ft.Text("Carregando categorias...")
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                self.page.update()
                
                # Faz a requisição assíncrona com timeout de 2 segundos
                url = f"{BACKEND_URL}/categories"
                print(f"DEBUG FRONTEND: Tentando conectar em {url}...")
                response = await self.async_http_client.get("/categories")
                response.raise_for_status()
                print("Processando JSON")
                self.categories = response.json()
                
                # Validar se a resposta está vazia
                if not self.categories:
                    print("Nenhuma categoria encontrada no banco")
                    content_container.content = ft.Column([
                        ft.Text("Nenhuma categoria encontrada no banco", color="red"),
                        ft.FilledButton(
                            "Recarregar categorias",
                            on_click=lambda e: asyncio.create_task(load_categories())
                        )
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                    print("Atualizando UI")
                    self.page.update()
                    return
                
                # Cria a lista de categorias
                categories_controls = []
                for cat in self.categories:
                    card = ft.Card(
                        content=ft.Container(
                            content=ft.ListTile(
                                title=ft.Text(cat["name"]),
                                subtitle=ft.Text(
                                    f"ID: {cat['id']} | Pai: {cat['parent_id'] or 'Nenhum'}"
                                ),
                            ),
                            padding=10,
                        )
                    )
                    categories_controls.append(card)
                
                # Substitui o conteúdo pelo resultado
                content_container.content = ft.ListView(
                    controls=categories_controls,
                    spacing=10,
                    padding=10,
                    expand=True
                )
                print("Atualizando UI")
                self.page.update()
                
            except Exception as ex:
                print(f"Erro na conexão: {ex}")
                # Timeout e Fallback: Remover "Carregando..." e adicionar botão para tentar novamente
                content_container.content = ft.Column([
                    ft.FilledButton("Erro na conexão. Tentar novamente", on_click=lambda e: asyncio.create_task(load_categories()))
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                print("Atualizando UI")
                self.page.update()
        
        # Botão para carregar dados iniciais
        def load_initial_categories(e):
            """Carrega dados iniciais quando o usuário clica"""
            asyncio.create_task(load_categories())
            # Desabilita o botão após carregar
            load_categories_button.disabled = True
            load_categories_button.update()
        
        load_categories_button = ft.FilledButton(
            "Carregar Dados",
            on_click=load_initial_categories,
        )
        
        return ft.Column(
            [
                ft.Text("Categorias", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Row(
                    [
                        load_categories_button,
                    ]
                ),
                content_container,
            ],
            expand=True,
        )

    def build_importar_view(self) -> ft.Column:
        """Constrói a visualização de Importação."""
        
        # Campo para URL da NFC-e
        url_field = ft.TextField(
            label="URL da NFC-e",
            hint_text="Cole aqui a URL de consulta da nota fiscal",
            multiline=True,
            min_lines=2,
            max_lines=4,
            expand=True,
        )
        
        use_browser_checkbox = ft.Checkbox(
            label="Usar navegador (mais lento, mas funciona com sites complexos)",
            value=False,
        )
        
        def on_import_url_click(e):
            """Importa nota fiscal pela URL."""
            url = url_field.value.strip()
            if not url:
                self.show_snackbar("Por favor, cole a URL da NFC-e", "orange")
                return
            
            try:
                # Mostra loading
                import_url_button.disabled = True
                import_url_button.text = "Importando..."
                self.page.update()
                
                # Chama o backend
                response = self.http_client.post(
                    "/import/url",
                    json={
                        "url": url,
                        "use_browser": use_browser_checkbox.value,
                    },
                )
                response.raise_for_status()
                result = response.json()
                
                # Mostra sucesso
                self.show_snackbar(
                    f"✓ Nota importada! {result['items_count']} itens de {result['seller_name']}",
                    "green",
                )
                
                # Limpa o campo
                url_field.value = ""
                
                # Atualiza a tabela de itens
                self.refresh_fiscal_items_table()
                
            except httpx.HTTPStatusError as ex:
                error_detail = ex.response.json().get("detail", str(ex))
                self.show_snackbar(f"Erro ao importar: {error_detail}", "red")
            except Exception as ex:
                self.show_snackbar(f"Erro ao importar: {str(ex)}", "red")
            finally:
                import_url_button.disabled = False
                import_url_button.text = "Importar da URL"
                self.page.update()
        
        import_url_button = ft.FilledButton(
            "Importar da URL",
            on_click=on_import_url_click,
        )
        
        # File picker para XML
        def on_file_picked(e: ft.FilePickerResultEvent):
            """Processa o arquivo XML selecionado."""
            if not e.files:
                return
            
            try:
                file_path = e.files[0].path
                
                # Mostra loading
                upload_xml_button.disabled = True
                upload_xml_button.text = "Importando..."
                self.page.update()
                
                # Lê o arquivo
                with open(file_path, "rb") as f:
                    files = {"file": (e.files[0].name, f, "application/xml")}
                    
                    # Envia para o backend
                    response = self.http_client.post("/import/xml", files=files)
                    response.raise_for_status()
                    result = response.json()
                
                # Mostra sucesso
                self.show_snackbar(
                    f"✓ XML importado! {result['items_count']} itens de {result['seller_name']}",
                    "green",
                )
                
                # Atualiza a tabela de itens
                self.refresh_fiscal_items_table()
                
            except Exception as ex:
                self.show_snackbar(f"Erro ao importar XML: {str(ex)}", "red")
            finally:
                upload_xml_button.disabled = False
                upload_xml_button.text = "Selecionar arquivo XML"
                self.page.update()
        
        file_picker = ft.FilePicker(on_result=on_file_picked)
        self.page.overlay.append(file_picker)
        
        def on_upload_xml_click(e):
            """Abre o seletor de arquivos."""
            file_picker.pick_files(
                allowed_extensions=["xml"],
                dialog_title="Selecione o arquivo XML da NF-e/NFC-e",
            )
        
        upload_xml_button = ft.FilledButton(
            "Selecionar arquivo XML",
            on_click=on_upload_xml_click,
        )
        
        # Tabela de itens importados
        items_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Produto")),
                ft.DataColumn(ft.Text("Quantidade")),
                ft.DataColumn(ft.Text("Preço Unit.")),
                ft.DataColumn(ft.Text("Total")),
                ft.DataColumn(ft.Text("Data Nota")),
            ],
            rows=[],
        )
        
        self.fiscal_items_table = items_table
        
        def load_fiscal_items():
            """Carrega os itens fiscais mais recentes."""
            self.refresh_fiscal_items_table()
        
        # Botão para carregar dados iniciais
        def load_initial_fiscal_items(e):
            """Carrega dados iniciais quando o usuário clica"""
            load_fiscal_items()
            # Desabilita o botão após carregar
            load_fiscal_items_button.disabled = True
            load_fiscal_items_button.update()
        
        load_fiscal_items_button = ft.FilledButton(
            "Carregar Dados",
            on_click=load_initial_fiscal_items,
        )
        
        return ft.Column(
            [
                ft.Text("Importar Notas Fiscais", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                
                # Seção de importação por URL
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("Importar por URL", size=18, weight=ft.FontWeight.BOLD),
                                url_field,
                                use_browser_checkbox,
                                import_url_button,
                            ],
                            spacing=10,
                        ),
                        padding=20,
                    )
                ),
                
                ft.Container(height=10),
                
                # Seção de importação por XML
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("Importar arquivo XML", size=18, weight=ft.FontWeight.BOLD),
                                ft.Text("Selecione um arquivo XML de NF-e ou NFC-e"),
                                upload_xml_button,
                            ],
                            spacing=10,
                        ),
                        padding=20,
                    )
                ),
                
                ft.Container(height=20),
                
                # Botão para carregar dados
                ft.Row(
                    [
                        load_fiscal_items_button,
                    ]
                ),
                
                # Tabela de itens importados
                ft.Text("Últimos Itens Importados", size=18, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=items_table,
                    border=ft.border.all(1, "#9e9e9e"),
                    border_radius=5,
                    padding=10,
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def refresh_fiscal_items_table(self):
        """Atualiza a tabela de itens fiscais."""
        try:
            # Busca os itens fiscais do backend
            url = f"{BACKEND_URL}/fiscal-items?limit=20"
            print(f"DEBUG FRONTEND: Tentando conectar em {url}...")
            response = self.http_client.get("/fiscal-items?limit=20")
            response.raise_for_status()
            items = response.json()
            
            if items:
                self.fiscal_items_table.rows = [
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(item["product_name"])),
                            ft.DataCell(ft.Text(f"{item['quantity']:.2f}")),
                            ft.DataCell(ft.Text(f"R$ {item['unit_price']:.2f}")),
                            ft.DataCell(ft.Text(f"R$ {item['total_price']:.2f}")),
                            ft.DataCell(ft.Text(f"{item['note_date']} - {item['seller_name']}")),
                        ]
                    )
                    for item in items
                ]
            else:
                self.fiscal_items_table.rows = [
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text("Nenhum item importado ainda")),
                            ft.DataCell(ft.Text("-")),
                            ft.DataCell(ft.Text("-")),
                            ft.DataCell(ft.Text("-")),
                            ft.DataCell(ft.Text("-")),
                        ]
                    )
                ]
            
            self.page.update()
            
        except Exception as ex:
            print(f"Erro ao atualizar tabela de itens: {ex}")
            # Em caso de erro, mostra uma mensagem na tabela
            self.fiscal_items_table.rows = [
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(f"Erro ao carregar itens: {str(ex)}")),
                        ft.DataCell(ft.Text("-")),
                        ft.DataCell(ft.Text("-")),
                        ft.DataCell(ft.Text("-")),
                        ft.DataCell(ft.Text("-")),
                    ]
                )
            ]
            if hasattr(self, 'page'):
                self.page.update()

    def show_snackbar(self, message: str, bgcolor: str):
        """Exibe uma mensagem snackbar."""
        snackbar = ft.SnackBar(
            content=ft.Text(message, color="white"),
            bgcolor=bgcolor,
            duration=3000,
        )
        self.page.snack_bar = snackbar
        snackbar.open = True
        self.page.update()

    def cleanup(self):
        """Limpa recursos ao fechar o app."""
        self.http_client.close()
        asyncio.run(self.async_http_client.aclose())


def main(page: ft.Page):
    """Função principal que inicializa o app."""
    print("DEBUG: Função main chamada")
    
    # Limpar a página antes de começar (persistência de estado)
    page.clean()
    page.on_connect = lambda _: print("DEBUG: Nova sessão estabelecida via WebSocket")
    
    # Adiciona manipulador de rota para forçar redraw na atualização (F5)
    def handle_route_change(route):
        print(f"DEBUG: on_route_change disparado para rota: {route.route}")
        page.clean()
        # Recreate the app after route change
        app = ERPApp(page)
        page.on_close = lambda _: app.cleanup()
    
    page.on_route_change = handle_route_change
    
    print("DEBUG: UI Montada, aguardando interação")
    
    try:
        page.clean()
        app = ERPApp(page)
        print("DEBUG: ERPApp instanciado com sucesso")
        page.on_close = lambda _: app.cleanup()
        print("DEBUG: main concluída com sucesso")
    except Exception as e:
        print(f"ERRO CRÍTICO: {e}")
        page.add(ft.Text(f"Erro ao carregar interface: {e}", color="red"))
        page.update()
    
    # Comando de Update: Garantido que existe ao final da função main
    page.update()


if __name__ == "__main__":
    ft.run(main, port=8081)  # Executa a aplicação na porta 8081 para evitar conflitos de cache
