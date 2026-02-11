import streamlit as st
import httpx
from typing import Optional


def fetch_data(url: str):
    """Fetch data from the backend API"""
    try:
        response = httpx.get(url)
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        st.error(f"Erro ao conectar ao backend: {str(e)}")
        return None
    except httpx.HTTPStatusError as e:
        st.error(f"Erro HTTP ao acessar o backend: {str(e)}")
        return None


@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_categories():
    """Get categories from backend with caching"""
    return fetch_data("http://127.0.0.1:8000/categories")


@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_transactions():
    """Get transactions from backend with caching"""
    return fetch_data("http://127.0.0.1:8000/transactions")


def main():
    # Set page configuration
    st.set_page_config(layout="wide", page_title="ERP Pessoal - Dignidade Financeira")
    
    # Main title
    st.title("ERP Pessoal - Dignidade Financeira")
    
    # Sidebar navigation
    st.sidebar.header("Menu de Navegação")
    page = st.sidebar.selectbox(
        "Selecione uma página:",
        ["Dashboard", "Categorias", "Importar XML/URL", "Histórico de Preços (Inflação)"]
    )
    
    if page == "Dashboard":
        st.header("Dashboard")
        st.write("Bem-vindo ao Dashboard do ERP Pessoal!")
        
        # Fetch data
        categories = get_categories()
        transactions = get_transactions()
        
        if categories:
            st.subheader("Total de Categorias")
            st.metric(label="Categorias", value=len(categories))
        
        if transactions:
            st.subheader("Total de Transações")
            st.metric(label="Transações", value=len(transactions))

    elif page == "Categorias":
        st.header("Categorias")
        
        # Fetch categories
        categories = get_categories()
        
        if categories:
            # Filter categories for specific family members
            family_members = ["Ana", "Carol", "Isabela", "Eduardo"]
            
            # Assuming categories might have a field like 'owner', 'person', 'family_member', or similar
            # This handles various possible structures of the category data
            if isinstance(categories, list):
                # Try to filter based on different possible keys
                filtered_categories = []
                
                for category in categories:
                    if isinstance(category, dict):
                        # Check for common key names that might contain person/family info
                        for key in ['owner', 'person', 'family_member', 'assigned_to', 'name']:
                            if key in category and category[key] in family_members:
                                filtered_categories.append(category)
                                break
                    else:
                        # If category is not a dict, just add it (fallback)
                        filtered_categories.append(category)
                
                st.subheader("Categorias Vinculadas à Família")
                if filtered_categories:
                    st.dataframe(filtered_categories)
                else:
                    st.info("Nenhuma categoria encontrada para os membros da família específicos.")
            else:
                st.write("Formato inesperado dos dados recebidos.")
        else:
            st.warning("Não foi possível carregar as categorias.")

    elif page == "Importar XML/URL":
        st.header("Importar XML/URL")
        
        # Text input for NFC-e URL
        url = st.text_input("Insira a URL da NFC-e:")
        
        # File uploader for XML
        xml_file = st.file_uploader("Ou faça upload do arquivo XML:", type=["xml"])
        
        if url:
            st.write(f"URL fornecida: {url}")
            # Here you would implement the logic to handle the URL
        
        if xml_file:
            st.write(f"Arquivo XML selecionado: {xml_file.name}")
            # Here you would implement the logic to handle the XML file

    elif page == "Histórico de Preços (Inflação)":
        st.header("Histórico de Preços (Inflação)")
        st.write("Funcionalidade de histórico de preços em desenvolvimento.")


if __name__ == "__main__":
    main()