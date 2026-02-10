"""Teste ultra básico"""
import flet as ft

def main(page: ft.Page):
    print("DEBUG: main() chamado")
    page.title = "Ultra Simples"
    page.padding = 20
    page.bgcolor = "white"
    
    print("DEBUG: Adicionando texto")
    page.add(
        ft.Text("TESTE - Se você vê isso, funciona!", size=40, color="black")
    )
    print("DEBUG: Texto adicionado, chamando update")
    page.update()
    print("DEBUG: Update chamado!")

if __name__ == "__main__":
    print("Iniciando app ultra simples...")
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8083)
