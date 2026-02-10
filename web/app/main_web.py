"""
ERP Pessoal - Frontend com Flet (modo WEB)
Interface principal com NavigationRail e integração com backend
"""
import flet as ft
from main import main

if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8081)
