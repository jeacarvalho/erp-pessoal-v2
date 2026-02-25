import streamlit as st
import httpx
import pandas as pd
import os
from typing import Optional
import cv2
import numpy as np
from PIL import Image
from pyzbar import pyzbar
from urllib.parse import quote

# Backend URL configurável via variável de ambiente
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


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
        response = httpx.get(
            f"{BACKEND_URL}/analytics/price-comparison?product_name={product_name}"
        )
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
    return fetch_data(f"{BACKEND_URL}/categories")


@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_transactions():
    """Get transactions from backend with caching"""
    return fetch_data(f"{BACKEND_URL}/transactions")


@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_fiscal_items():
    """Get fiscal items from backend with caching"""
    return fetch_data(f"{BACKEND_URL}/fiscal-items")


@st.cache_data(ttl=60)
def get_sellers():
    """Get sellers with history from backend with caching"""
    return fetch_data(f"{BACKEND_URL}/analytics/sellers/with-history")


def fetch_seller_trends(seller_name: str):
    """Fetch seller trends data from backend"""
    try:
        response = httpx.get(
            f"{BACKEND_URL}/analytics/seller-trends?seller_name={quote(seller_name, safe='')}"
        )
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        st.error(f"Erro ao conectar ao backend: {str(e)}")
        return None
    except httpx.HTTPStatusError as e:
        st.error(f"Erro HTTP ao acessar o backend: {str(e)}")
        return None


def analyze_flyer(image_file):
    """Send flyer image to backend for OCR analysis"""
    try:
        files = {"file": (image_file.name, image_file.getvalue(), image_file.type)}
        response = httpx.post(
            f"{BACKEND_URL}/analytics/analyze-flyer", files=files, timeout=120.0
        )
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        st.error(f"Erro ao conectar ao backend: {str(e)}")
        return None
    except httpx.HTTPStatusError as e:
        st.error(f"Erro HTTP ao acessar o backend: {str(e)}")
        return None


def main():
    # Set page configuration
    st.set_page_config(layout="wide", page_title="ERP Pessoal - Dignidade Financeira")

    # Main title
    st.title("ERP Pessoal - Dignidade Financeira")

    # Sidebar navigation
    st.sidebar.header("Menu de Navegação")
    page = st.sidebar.selectbox(
        "Selecione uma página:",
        [
            "Dashboard",
            "Categorias",
            "Importar XML/URL",
            "Histórico de Preços (Inflação)",
            "Comparação de Preços",
            "Scanner de Produtos",
            "Analisar Encarte",
        ],
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
                        for key in [
                            "owner",
                            "person",
                            "family_member",
                            "assigned_to",
                            "name",
                        ]:
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
                    st.info(
                        "Nenhuma categoria encontrada para os membros da família específicos."
                    )
            else:
                st.write("Formato inesperado dos dados recebidos.")
        else:
            st.warning("Não foi possível carregar as categorias.")

    elif page == "Importar XML/URL":
        st.header("Importar XML/URL")

        # Text input for NFC-e URL
        url = st.text_input("Insira a URL da NFC-e:")

        # Checkbox to use browser for scraping (optional)
        use_browser = st.checkbox(
            "Usar navegador para scraping (mais lento mas mais confiável)"
        )

        # File uploader for XML (accepts multiple files)
        xml_files = st.file_uploader(
            "Ou faça upload de arquivos XML:", type=["xml"], accept_multiple_files=True
        )

        # Import button
        import_button = st.button("Importar")

        if import_button:
            if url:
                with st.spinner("Importando dados da URL..."):
                    try:
                        # Call backend API for URL import
                        import_payload = {"url": url, "use_browser": use_browser}
                        response = httpx.post(
                            f"{BACKEND_URL}/import/url", json=import_payload
                        )

                        if response.status_code == 200:
                            result = response.json()
                            st.success(f"Nota fiscal importada com sucesso!")
                            st.write(f"ID da Nota: {result['note_id']}")
                            st.write(f"Quantidade de Itens: {result['items_count']}")
                            st.write(f"Estabelecimento: {result['seller_name']}")
                            st.write(f"Valor Total: R$ {result['total_amount']:.2f}")
                        else:
                            st.error(
                                f"Erro na importação: {response.status_code} - {response.text}"
                            )
                    except Exception as e:
                        st.error(f"Erro ao conectar ao backend: {str(e)}")

            elif xml_files:
                for i, xml_file in enumerate(xml_files):
                    with st.spinner(f"Importando XML {i + 1} de {len(xml_files)}..."):
                        try:
                            # Prepare file for upload
                            files = {
                                "file": (
                                    xml_file.name,
                                    xml_file.getvalue(),
                                    "application/xml",
                                )
                            }

                            # Call backend API for XML import (SEFAZ RJ)
                            response = httpx.post(
                                f"{BACKEND_URL}/import/xml-rj", files=files
                            )

                            if response.status_code == 200:
                                result = response.json()
                                st.success(
                                    f"Nota fiscal {xml_file.name} importada com sucesso!"
                                )
                                st.write(f"ID da Nota: {result['note_id']}")
                                st.write(
                                    f"Quantidade de Itens: {result['items_count']}"
                                )
                                st.write(f"Estabelecimento: {result['seller_name']}")
                                st.write(
                                    f"Valor Total: R$ {result['total_amount']:.2f}"
                                )
                            else:
                                st.error(
                                    f"Erro na importação do XML {xml_file.name}: {response.status_code} - {response.text}"
                                )
                        except Exception as e:
                            st.error(
                                f"Erro ao conectar ao backend para o XML {xml_file.name}: {str(e)}"
                            )
            else:
                st.warning(
                    "Por favor, insira uma URL ou faça upload de um ou mais arquivos XML."
                )

    elif page == "Histórico de Preços (Inflação)":
        st.header("Histórico de Preços (Inflação)")

        sellers = get_sellers()

        if sellers:
            selected_seller = st.selectbox(
                "Selecione o Vendedor:",
                options=sellers,
            )

            if selected_seller:
                trends_data = fetch_seller_trends(selected_seller)

                if trends_data and trends_data.get("products"):
                    products = trends_data["products"]

                    sorted_products = sorted(
                        products,
                        key=lambda x: (
                            x.get("variation_percent") is None,
                            -(x.get("variation_percent") or 0),
                        ),
                    )

                    top_10 = sorted_products[:10]

                    if top_10:
                        st.subheader("Top 10 Produtos (por variação de preço)")
                        table_data = []
                        for p in top_10:
                            last_price = p["price_history"][0]
                            prev_price = (
                                p["price_history"][1]
                                if len(p["price_history"]) > 1
                                else None
                            )
                            variation = p.get("variation_percent")

                            table_data.append(
                                {
                                    "Produto": p["product_name"],
                                    "Último Preço (R$)": f"{last_price:.2f}",
                                    "Preço Anterior (R$)": f"{prev_price:.2f}"
                                    if prev_price
                                    else "-",
                                    "Variação (%)": f"{variation:.2f}%"
                                    if variation is not None
                                    else "-",
                                }
                            )

                        if table_data:
                            df = pd.DataFrame(table_data)
                            st.dataframe(df, use_container_width=True)

                        villains = [
                            p for p in top_10 if p.get("variation_percent") is not None
                        ]
                        if villains:
                            villains_df = pd.DataFrame(
                                {
                                    "Produto": [
                                        p["product_name"][:25] + "..."
                                        if len(p["product_name"]) > 25
                                        else p["product_name"]
                                        for p in villains
                                    ],
                                    "Variação (%)": [
                                        p["variation_percent"] for p in villains
                                    ],
                                }
                            )
                            if not villains_df.empty:
                                villains_df = villains_df.set_index("Produto")
                                st.bar_chart(villains_df)
                    else:
                        st.info("Sem dados de tendências para este vendedor.")
                else:
                    st.info(f"Sem dados de tendências para {selected_seller}.")
        else:
            st.warning("Nenhum vendedor encontrado.")

    elif page == "Comparação de Preços":
        st.header("Comparação de Preços entre Mercados")

        # Fetch all fiscal items to populate product selection
        fiscal_items = get_fiscal_items()

        if fiscal_items:
            # Extract unique product names for the selectbox
            product_names = list(set([item["product_name"] for item in fiscal_items]))
            product_names.sort()

            # Create a selectbox for product selection
            selected_product = st.selectbox(
                "Selecione um produto para comparar preços:", options=product_names
            )

            if selected_product:
                # Fetch price comparison data for the selected product
                comparison_data = fetch_price_comparison(selected_product)

                if comparison_data:
                    # Convert to DataFrame for easier manipulation
                    df = pd.DataFrame(comparison_data)

                    if not df.empty:
                        # Prepare data for visualization
                        df["date"] = pd.to_datetime(df["date"])

                        # Calculate average prices per seller
                        avg_prices = (
                            df.groupby("seller_name")["unit_price"]
                            .mean()
                            .sort_values(ascending=True)  # type: ignore[call-overload]
                        )

                        # Find the cheapest seller
                        cheapest_seller = avg_prices.index[0]
                        cheapest_avg_price = avg_prices.iloc[0]
                        other_sellers_avg = avg_prices.iloc[1:].mean()

                        # Calculate percentage difference
                        if other_sellers_avg > 0:
                            percent_cheaper = (
                                (other_sellers_avg - cheapest_avg_price)
                                / other_sellers_avg
                            ) * 100
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
                            unsafe_allow_html=True,
                        )

                        # Create scatter chart showing prices over time
                        st.subheader(
                            f"Variação de Preços ao Longo do Tempo para '{selected_product}'"
                        )
                        st.scatter_chart(
                            data=df,
                            x="date",
                            y="unit_price",
                            color="seller_name",
                            size=100,
                            height=500,
                        )

                        # Show detailed data table
                        st.subheader("Dados Detalhados")
                        detailed_df = df[
                            ["product_name", "unit_price", "date", "seller_name"]
                        ]
                        detailed_df = detailed_df.sort_values("date", ascending=False)  # type: ignore[call-overload]
                        st.dataframe(detailed_df)
                    else:
                        st.warning("Nenhum dado de preço encontrado para este produto.")
                else:
                    st.error("Falha ao buscar dados de comparação de preços.")
            else:
                st.info("Selecione um produto para ver a comparação de preços.")
        else:
            st.warning("Não foi possível carregar os dados de itens fiscais.")

    elif page == "Scanner de Produtos":
        st.header("Scanner de Produtos - Leitura de Código de Barras")

        # Camera input for barcode scanning
        camera_image = st.camera_input(
            "Aponte a câmera para o código de barras do produto"
        )

        if camera_image is not None:
            # Convert the image to OpenCV format
            bytes_data = camera_image.getvalue()
            np_array = np.frombuffer(bytes_data, np.uint8)
            img = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

            # Decode the barcode
            decoded_objects = pyzbar.decode(img)

            if decoded_objects:
                ean_code = decoded_objects[0].data.decode("utf-8")
                st.success(f"Código EAN detectado: **{ean_code}**")

                # Check if the EAN exists in the database
                try:
                    response = httpx.get(f"{BACKEND_URL}/products/eans/{ean_code}")
                    if response.status_code == 200:
                        product_info = response.json()
                        st.info(
                            f"Produto já cadastrado: {product_info.get('name_standard', 'Nome não disponível')}"
                        )

                        # Show option to link orphan fiscal items to this EAN
                        st.subheader("Vincular itens órfãos a este EAN")

                        # Fetch orphan fiscal items (items without product_ean)
                        try:
                            fiscal_response = httpx.get(
                                f"{BACKEND_URL}/fiscal-items/orphans"
                            )
                            if fiscal_response.status_code == 200:
                                orphan_items = fiscal_response.json()

                                if orphan_items:
                                    # Create a selectbox with orphan items' raw descriptions
                                    descriptions = [
                                        item["product_name"] for item in orphan_items
                                    ]
                                    selected_description = st.selectbox(
                                        "Selecione um item órfão para vincular a este EAN:",
                                        options=descriptions,
                                    )

                                    if selected_description:
                                        # Find the selected item details
                                        selected_item = next(
                                            item
                                            for item in orphan_items
                                            if item["product_name"]
                                            == selected_description
                                        )

                                        # Button to create mapping
                                        if st.button("Vincular Item a este EAN"):
                                            mapping_payload = {
                                                "raw_description": selected_item[
                                                    "product_name"
                                                ],
                                                "seller_name": selected_item.get(
                                                    "seller_name", "Desconhecido"
                                                ),
                                                "product_ean": int(ean_code),
                                            }

                                            try:
                                                mapping_response = httpx.post(
                                                    f"{BACKEND_URL}/product-mappings/",
                                                    json=mapping_payload,
                                                )
                                                if mapping_response.status_code == 200:
                                                    st.success(
                                                        f"Sistema aprendeu a traduzir '{selected_description}' para o EAN {ean_code}! "
                                                        f"Este vínculo será usado nas próximas importações."
                                                    )
                                                else:
                                                    st.error(
                                                        f"Erro ao criar vínculo: {mapping_response.text}"
                                                    )
                                            except Exception as e:
                                                st.error(
                                                    f"Erro de conexão ao criar vínculo: {str(e)}"
                                                )
                                    else:
                                        st.info("Selecione um item para vincular.")
                                else:
                                    st.info(
                                        "Não há itens órfãos disponíveis para vinculação."
                                    )
                            else:
                                st.warning("Não foi possível carregar os itens órfãos.")
                        except Exception as e:
                            st.error(f"Erro ao buscar itens órfãos: {str(e)}")
                    else:
                        st.warning(
                            "Este EAN ainda não está cadastrado no sistema. Complete o cadastro abaixo:"
                        )

                        # Form to register the product
                        with st.form(key="register_product"):
                            name_standard = st.text_input("Nome Amigável do Produto")

                            # Get family member options and map to category IDs
                            family_member_to_category = {
                                "Ana": 21,  # Ana category ID
                                "Carol": 20,  # Carol category ID
                                "Eduardo": 22,  # Eduardo category ID
                                "Isabela": 12,  # Isabela category ID (Ajuda Bruna Isabela)
                            }
                            owner = st.selectbox(
                                "Responsável pelo produto",
                                list(family_member_to_category.keys()),
                            )

                            submit_button = st.form_submit_button("Cadastrar Produto")

                            if submit_button and name_standard and owner:
                                # Register the product
                                payload = {
                                    "ean": ean_code,
                                    "name_standard": name_standard,
                                    "category_id": family_member_to_category[owner],
                                }

                                try:
                                    register_response = httpx.post(
                                        f"{BACKEND_URL}/products/eans/",
                                        json=payload,
                                    )
                                    if register_response.status_code == 200:
                                        st.success(
                                            f"Produto cadastrado com sucesso! EAN: {ean_code}, Nome: {name_standard}"
                                        )

                                        # After successful product registration, create a mapping for the raw description
                                        # Get the raw description from the orphan items if any
                                        try:
                                            fiscal_response = httpx.get(
                                                f"{BACKEND_URL}/fiscal-items/orphans"
                                            )
                                            if fiscal_response.status_code == 200:
                                                orphan_items = fiscal_response.json()

                                                if orphan_items:
                                                    # Find an orphan item matching the scanned product name
                                                    for item in orphan_items:
                                                        # Create mapping for this raw description to the newly registered EAN
                                                        mapping_payload = {
                                                            "raw_description": item[
                                                                "product_name"
                                                            ],
                                                            "seller_name": item.get(
                                                                "seller_name",
                                                                "Desconhecido",
                                                            ),
                                                            "product_ean": int(
                                                                ean_code
                                                            ),
                                                        }

                                                        mapping_response = httpx.post(
                                                            f"{BACKEND_URL}/product-mappings/",
                                                            json=mapping_payload,
                                                        )
                                                        if (
                                                            mapping_response.status_code
                                                            == 200
                                                        ):
                                                            st.success(
                                                                f"Sistema aprendeu a traduzir '{item['product_name']}' para o EAN {ean_code}! "
                                                                f"Este vínculo será usado nas próximas importações."
                                                            )
                                                            break  # Only create one mapping for the new EAN
                                                        else:
                                                            st.error(
                                                                f"Erro ao criar vínculo: {mapping_response.text}"
                                                            )
                                                            break
                                        except Exception as e:
                                            st.error(
                                                f"Erro ao tentar criar vínculo automático: {str(e)}"
                                            )
                                    else:
                                        st.error(
                                            f"Erro ao cadastrar produto: {register_response.text}"
                                        )
                                except Exception as e:
                                    st.error(
                                        f"Erro de conexão ao cadastrar produto: {str(e)}"
                                    )
                except Exception as e:
                    st.error(f"Erro ao verificar o EAN no banco de dados: {str(e)}")
            else:
                st.warning(
                    "Nenhum código de barras detectado. Tente ajustar a iluminação ou a posição do produto."
                )
        else:
            st.info("Aguardando captura de imagem...")

    elif page == "Analisar Encarte":
        st.header("Analisar Encarte de Ofertas")

        st.markdown("""
        Envie uma imagem de encarte de ofertas (screenshot de site, foto de folheto, etc.)
        para comparar os preços com seu histórico de compras.
        """)

        uploaded_file = st.file_uploader(
            "Escolha um arquivo (imagem ou PDF):",
            type=["png", "jpg", "jpeg", "webp", "pdf"],
            help="Aceita imagens PNG, JPG, JPEG, WebP ou PDF",
        )

        if uploaded_file is not None:
            is_pdf = uploaded_file.type == "application/pdf"

            col1, col2 = st.columns([1, 2])

            with col1:
                if is_pdf:
                    st.info(f"📄 PDF enviado: {uploaded_file.name}")
                else:
                    st.image(
                        uploaded_file, caption="Encarte enviado", use_column_width=True
                    )

            with col2:
                if st.button("Analisar Ofertas", type="primary"):
                    with st.spinner("Analisando encarte com OCR..."):
                        results = analyze_flyer(uploaded_file)

                        if results:
                            if len(results) == 0:
                                st.warning(
                                    "Nenhum produto do encarte foi encontrado no seu histórico de compras. "
                                    "Importe algumas notas fiscais primeiro!"
                                )
                            else:
                                st.success(
                                    f"Encontradas {len(results)} ofertas comparadas!"
                                )

                                deals = [r for r in results if r.get("is_deal")]
                                not_deals = [r for r in results if not r.get("is_deal")]

                                if deals:
                                    st.markdown("### 🔥 Ofertas Bomba!")
                                    for deal in deals:
                                        savings = (
                                            deal["base_avg_price"] - deal["offer_price"]
                                        )
                                        percent = (
                                            savings / deal["base_avg_price"]
                                        ) * 100
                                        st.markdown(
                                            f"""
                                            <div style="background-color: #d4edda; padding: 10px; border-radius: 5px; margin: 5px 0;">
                                                <strong>{deal["product_name"]}</strong><br>
                                                💰 Oferta: <strong>R$ {deal["offer_price"]:.2f}</strong><br>
                                                📊 Média anterior: R$ {deal["base_avg_price"]:.2f}<br>
                                                🎉 Economia: <strong>R$ {savings:.2f} ({percent:.1f}%)</strong>
                                            </div>
                                            """,
                                            unsafe_allow_html=True,
                                        )

                                if not_deals:
                                    st.markdown("### ℹ️ Preços Normais (sem desconto)")
                                    for item in not_deals:
                                        st.markdown(
                                            f"""
                                            <div style="background-color: #f8f9fa; padding: 8px; border-radius: 5px; margin: 5px 0;">
                                                <strong>{item["product_name"]}</strong><br>
                                                💰 Oferta: R$ {item["offer_price"]:.2f} | 
                                                📊 Média: R$ {item["base_avg_price"]:.2f}
                                            </div>
                                            """,
                                            unsafe_allow_html=True,
                                        )

                                st.markdown("### 📋 Detalhes")
                                df = pd.DataFrame(results)
                                st.dataframe(df, use_container_width=True)
                        elif results is None:
                            st.error(
                                "Erro ao analisar encarte. Verifique se o backend está rodando."
                            )
                        else:
                            st.info(
                                "Nenhum produto do encarte encontrado no seu histórico de compras. "
                                "Importe algumas notas fiscais desses produtos primeiro!"
                            )


if __name__ == "__main__":
    main()
