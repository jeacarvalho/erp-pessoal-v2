"""Teste com UI simplificada"""
import flet as ft

class SimpleApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Teste Simples"
        self.setup_ui()
    
    def setup_ui(self):
        # NavigationRail simples
        nav = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            destinations=[
                ft.NavigationRailDestination(label="Item 1"),
                ft.NavigationRailDestination(label="Item 2"),
            ],
        )
        
        # Conteúdo simples
        content = ft.Container(
            content=ft.Column([
                ft.Text("Título Teste", size=30),
                ft.Text("Se você está vendo isso, o layout está funcionando!"),
                ft.ElevatedButton("Botão Teste"),
            ]),
            expand=True,
            padding=20,
        )
        
        # Layout
        self.page.add(
            ft.Row([
                nav,
                ft.VerticalDivider(width=1),
                content,
            ], expand=True)
        )
        
        print("DEBUG: UI simplificada montada!")
        self.page.update()

def main(page: ft.Page):
    SimpleApp(page)

if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8082)
