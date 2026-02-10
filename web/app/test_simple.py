"""Teste simples do Flet"""
import flet as ft

def main(page: ft.Page):
    page.title = "Teste Simples"
    page.add(
        ft.Text("Olá! Se você está vendo isso, o Flet está funcionando!", size=30)
    )

if __name__ == "__main__":
    ft.app(target=main)
