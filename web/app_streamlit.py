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


def fetch_price_comparison(product_name: str):
    """Fetch price comparison data from the backend API"""
    try:
        response = httpx.get(f"http://127.0.0.1:8000/analytics/price-comparison?product_name={product_name}")
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
def get_fiscal_items():
    """Get fiscal items from backend with caching"""
    return fetch_data("http://127.0.0.1:8000/fiscal-items")


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
        
        # Checkbox to use browser for scraping (optional)
        use_browser = st.checkbox("Usar navegador para scraping (mais lento mas mais confiável)")
        
        # File uploader for XML
        xml_file = st.file_uploader("Ou faça upload do arquivo XML:", type=["xml"])
        
        # Import button
        import_button = st.button("Importar")
        
        if import_button:
            if url:
                with st.spinner("Importando dados da URL..."):
                    try:
                        # Call backend API for URL import
                        import_payload = {"url": url, "use_browser": use_browser}
                        response = httpx.post("http://127.0.0.1:8000/import/url", json=import_payload)
                        
                        if response.status_code == 200:
                            result = response.json()
                            st.success(f"Nota fiscal importada com sucesso!")
                            st.write(f"ID da Nota: {result['note_id']}")
                            st.write(f"Quantidade de Itens: {result['items_count']}")
                            st.write(f"Estabelecimento: {result['seller_name']}")
                            st.write(f"Valor Total: R$ {result['total_amount']:.2f}")
                        else:
                            st.error(f"Erro na importação: {response.status_code} - {response.text}")
                    except Exception as e:
                        st.error(f"Erro ao conectar ao backend: {str(e)}")
            
            elif xml_file:
                with st.spinner("Importando dados do XML..."):
                    try:
                        # Prepare file for upload
                        files = {"file": (xml_file.name, xml_file.getvalue(), "application/xml")}
                        
                        # Call backend API for XML import
                        response = httpx.post("http://127.0.0.1:8000/import/xml", files=files)
                        
                        if response.status_code == 200:
                            result = response.json()
                            st.success(f"Nota fiscal importada com sucesso!")
                            st.write(f"ID da Nota: {result['note_id']}")
                            st.write(f"Quantidade de Itens: {result['items_count']}")
                            st.write(f"Estabelecimento: {result['seller_name']}")
                            st.write(f"Valor Total: R$ {result['total_amount']:.2f}")
                        else:
                            st.error(f"Erro na importação: {response.status_code} - {response.text}")
                    except Exception as e:
                        st.error(f"Erro ao conectar ao backend: {str(e)}")
            else:
                st.warning("Por favor, insira uma URL ou faça upload de um arquivo XML.")

    elif page == "Histórico de Preços (Inflação)":
        st.header("Histórico de Preços (Inflação)")
        st.write("Funcionalidade de histórico de preços em desenvolvimento.")
    
    elif page == "Comparação de Preços":
        st.header("Comparação de Preços entre Mercados")
        
        # Fetch all fiscal items to populate product selection
        fiscal_items = get_fiscal_items()
        
        if fiscal_items:
            # Extract unique product names for the selectbox
            product_names = list(set([item['product_name'] for item in fiscal_items]))
            product_names.sort()
            
            # Create a selectbox for product selection
            selected_product = st.selectbox("Selecione um produto para comparar preços:", options=product_names)
            
            if selected_product:
                # Fetch price comparison data for the selected product
                comparison_data = fetch_price_comparison(selected_product)
                
                if comparison_data:
                    # Convert to DataFrame for easier manipulation
                    df = pd.DataFrame(comparison_data)
                    
                    if not df.empty:
                        # Prepare data for visualization
                        df['date'] = pd.to_datetime(df['date'])
                        
                        # Calculate average prices per seller
                        avg_prices = df.groupby('seller_name')['unit_price'].mean().sort_values()
                        
                        # Find the cheapest seller
                        cheapest_seller = avg_prices.index[0]
                        cheapest_avg_price = avg_prices.iloc[0]
                        other_sellers_avg = avg_prices.iloc[1:].mean()
                        
                        # Calculate percentage difference
                        if other_sellers_avg > 0:
                            percent_cheaper = ((other_sellers_avg - cheapest_avg_price) / other_sellers_avg) * 100
                        else:
                            percent_cheaper = 0
                        
                        # Display alert card
                        st.markdown(
                            f"""
                            <div style="background-color: #d4edda; padding: 15px; border-radius: 8px; border-left: 5px solid #28a745;">
                                <h4 style="color: #155724;">Alerta de Economia 📈</h4>
                                <p style="color: #155724; font-size: 16px;">
                                    Este item está, em média, <strong>{percent_cheaper:.0f}% mais barato</strong> no <strong>{cheapest_seller}</strong>.
                                </p>
                            </div>
                            """, 
                            unsafe_allow_html=True
                        )
                        
                        # Create scatter chart showing prices over time
                        st.subheader(f"Variação de Preços ao Longo do Tempo para '{selected_product}'")
                        st.scatter_chart(
                            data=df,
                            x='date',
                            y='unit_price',
                            color='seller_name',
                            size=100,
                            height=500
                        )
                        
                        # Show detailed data table
                        st.subheader("Dados Detalhados")
                        st.dataframe(df[['product_name', 'unit_price', 'date', 'seller_name']].sort_values('date', ascending=False))
                    else:
                        st.warning("Nenhum dado de preço encontrado para este produto.")
                else:
                    st.error("Falha ao buscar dados de comparação de preços.")
            else:
                st.info("Selecione um produto para ver a comparação de preços.")
        else:
            st.warning("Não foi possível carregar os dados de itens fiscais.")


if __name__ == "__main__":
    main()