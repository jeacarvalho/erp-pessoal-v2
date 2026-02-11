import streamlit as st
import httpx
import pandas as pd
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


@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_price_comparison(product_name: str):
    """Get price comparison data from backend with caching"""
    return fetch_data(f"http://127.0.0.1:8000/analytics/price-comparison?product_name={product_name}")


def main():
    # Set page configuration
    st.set_page_config(layout="wide", page_title="ERP Pessoal - Dignidade Financeira")
    
    # Main title
    st.title("ERP Pessoal - Dignidade Financeira")
    
    # Sidebar navigation
    st.sidebar.header("Menu de Navegação")
    page = st.sidebar.selectbox(
        "Selecione uma página:",
        ["Dashboard", "Categorias", "Importar XML/URL", "Histórico de Preços (Inflação)", "Comparação de Preços"]
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
    
    elif page == "Comparação de Preços":
        st.header("Comparação de Preços entre Mercados")
        
        # Get all products for the select box
        all_items_response = fetch_data("http://127.0.0.1:8000/fiscal-items")
        
        if all_items_response:
            # Extract unique product names
            product_names = list(set([item['product_name'] for item in all_items_response]))
            
            # Create a select box for product selection
            selected_product = st.selectbox(
                "Selecione um produto para comparar preços:",
                sorted(product_names)
            )
            
            if selected_product:
                # Fetch price comparison data
                price_data = get_price_comparison(selected_product)
                
                if price_data:
                    # Convert to DataFrame for easier manipulation
                    df = pd.DataFrame(price_data)
                    
                    if not df.empty:
                        # Display average price per seller
                        avg_prices = df.groupby('seller_name')['unit_price'].mean().sort_values()
                        
                        # Find the cheapest seller
                        cheapest_seller = avg_prices.index[0]
                        cheapest_price = avg_prices.iloc[0]
                        overall_avg = df['unit_price'].mean()
                        
                        # Calculate percentage difference
                        if overall_avg > 0:
                            percent_diff = ((overall_avg - cheapest_price) / overall_avg) * 100
                            
                            # Display savings alert
                            st.success(f"Este item está, em média, {percent_diff:.0f}% mais barato no {cheapest_seller}")
                        
                        # Prepare data for scatter chart (convert date to datetime)
                        df['date'] = pd.to_datetime(df['date'])
                        
                        # Create scatter chart showing prices over time by seller
                        st.subheader(f"Variação de Preços ao Longo do Tempo - {selected_product}")
                        
                        # Using st.scatter_chart to show price vs time grouped by seller
                        st.scatter_chart(
                            data=df,
                            x='date',
                            y='unit_price',
                            color='seller_name',
                            size=100  # Fixed size for all points
                        )
                        
                        # Show raw data table
                        st.subheader("Dados de Preços")
                        st.dataframe(df[['product_name', 'seller_name', 'unit_price', 'date']].sort_values('date', ascending=False))
                    else:
                        st.info("Nenhum dado de preço encontrado para este produto.")
                else:
                    st.error("Erro ao buscar dados de comparação de preços.")
            else:
                st.info("Selecione um produto para ver a comparação de preços.")
        else:
            st.error("Erro ao buscar lista de produtos.")


if __name__ == "__main__":
    main()