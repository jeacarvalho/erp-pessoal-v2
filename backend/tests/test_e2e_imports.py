"""
Teste de ponta a ponta (E2E) para validação completa do fluxo de importação de notas fiscais.

Este teste simula todo o processo:
1. Upload de XML ou importação via URL
2. Persistência dos dados
3. Consulta dos dados importados via API
4. Validação de consistência dos dados
"""

import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app, get_db
from app.seed import get_session_factory
from app.models import Base


def test_e2e_xml_import_and_query():
    """
    Teste E2E completo: importa XML e verifica os dados consultados.
    """
    # Setup do banco de dados para testes
    engine = create_engine("sqlite:///test_e2e.db", echo=True)
    TestingSessionLocal = get_session_factory("sqlite:///test_e2e.db")
    
    # Cria as tabelas
    Base.metadata.create_all(bind=engine)
    
    # Substitui a dependência de banco de dados no app
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    client = TestClient(app)
    
    # Dados de exemplo para um XML de NFC-e
    xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<nfeProc versao="4.00" xmlns="http://www.portalfiscal.inf.br/nfe">
    <NFe>
        <infNFe Id="NFe12345678901234567890123456789012345678901234567890" versao="4.00">
            <ide>
                <cUF>35</cUF>
                <cNF>12345678</cNF>
                <natOp>VENDA AO CONSUMIDOR</natOp>
                <mod>65</mod>
                <serie>1</serie>
                <nNF>12345</nNF>
                <dhEmi>2023-05-15T10:30:00-03:00</dhEmi>
                <tpNF>0</tpNF>
                <cMunFG>3550308</cMunFG>
                <tpImp>1</tpImp>
                <tpEmis>1</tpEmis>
                <cDV>0</cDV>
                <tpAmb>2</tpAmb>
                <finNFe>1</finNFe>
                <indFinal>1</indFinal>
                <indPres>1</indPres>
                <procEmi>0</procEmi>
                <verProc>8.51</verProc>
            </ide>
            <emit>
                <CNPJ>12345678000195</CNPJ>
                <xNome>LOJA EXEMPLO LTDA</xNome>
                <xFant>LOJA EXEMPLO</xFant>
                <enderEmit>
                    <xLgr>RUA DOS EXEMPLOS</xLgr>
                    <nro>100</nro>
                    <xBairro>CENTRO</xBairro>
                    <cMun>3550308</cMun>
                    <xMun>SÃO PAULO</xMun>
                    <UF>SP</UF>
                    <CEP>01000000</CEP>
                    <cPais>1058</cPais>
                    <xPais>BRASIL</xPais>
                    <fone>11999999999</fone>
                </enderEmit>
                <IE>123456789</IE>
            </emit>
            <det nItem="1">
                <prod>
                    <cProd>PROD001</cProd>
                    <cEAN/>
                    <xProd>ARROZ TIPO 1 KG</xProd>
                    <NCM>10063010</NCM>
                    <CFOP>5405</CFOP>
                    <uCom>UN</uCom>
                    <qCom>2.0000</qCom>
                    <vUnCom>15.0000000000</vUnCom>
                    <vProd>30.00</vProd>
                    <cEANTrib/>
                    <uTrib>UN</uTrib>
                    <qTrib>2.0000</qTrib>
                    <vUnTrib>15.0000000000</vUnTrib>
                    <indTot>1</indTot>
                </prod>
                <imposto>
                    <vTotTrib>0.00</vTotTrib>
                </imposto>
            </det>
            <det nItem="2">
                <prod>
                    <cProd>PROD002</cProd>
                    <cEAN/>
                    <xProd>FEIJAO PRETO 1KG</xProd>
                    <NCM>10063020</NCM>
                    <CFOP>5405</CFOP>
                    <uCom>UN</uCom>
                    <qCom>1.0000</qCom>
                    <vUnCom>8.5000000000</vUnCom>
                    <vProd>8.50</vProd>
                    <cEANTrib/>
                    <uTrib>UN</uTrib>
                    <qTrib>1.0000</qTrib>
                    <vUnTrib>8.5000000000</vUnTrib>
                    <indTot>1</indTot>
                </prod>
                <imposto>
                    <vTotTrib>0.00</vTotTrib>
                </imposto>
            </det>
            <total>
                <ICMSTot>
                    <vBC>0.00</vBC>
                    <vICMS>0.00</vICMS>
                    <vICMSDeson>0.00</vICMSDeson>
                    <vFCP>0.00</vFCP>
                    <vBCST>0.00</vBCST>
                    <vST>0.00</vST>
                    <vFCPST>0.00</vFCPST>
                    <vFCPSTRet>0.00</vFCPSTRet>
                    <vProd>38.50</vProd>
                    <vFrete>0.00</vFrete>
                    <vSeg>0.00</vSeg>
                    <vDesc>0.00</vDesc>
                    <vII>0.00</vII>
                    <vIPI>0.00</vIPI>
                    <vIPIDevol>0.00</vIPIDevol>
                    <vPIS>0.00</vPIS>
                    <vCOFINS>0.00</vCOFINS>
                    <vOutro>0.00</vOutro>
                    <vNF>38.50</vNF>
                    <vTotTrib>0.00</vTotTrib>
                </ICMSTot>
            </total>
        </infNFe>
    </NFe>
    <protNFe versao="4.00">
        <infProt>
            <tpAmb>2</tpAmb>
            <verAplic>8.51</verAplic>
            <chNFe>12345678901234567890123456789012345678901234567890</chNFe>
            <dhRecbto>2023-05-15T10:31:00-03:00</dhRecbto>
            <nProt>123456789012345</nProt>
            <digVal>jXcm7Q0jWgRzrGwK8JZBkQ==</digVal>
            <cStat>100</cStat>
            <xMotivo>Autorizado o uso da NF-e</xMotivo>
        </infProt>
    </protNFe>
</nfeProc>'''

    # Cria um arquivo temporário com o conteúdo XML
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as temp_file:
        temp_file.write(xml_content)
        temp_file_path = Path(temp_file.name)

    try:
        # Realiza o upload do XML
        with open(temp_file_path, 'rb') as f:
            response = client.post(
                "/import/xml",
                files={"file": ("test_nfe.xml", f, "application/xml")}
            )
        
        assert response.status_code == 200
        response_data = response.json()
        assert "note_id" in response_data
        assert response_data["items_count"] == 2
        assert response_data["seller_name"] == "LOJA EXEMPLO LTDA"
        assert response_data["total_amount"] == 38.5
        
        note_id = response_data["note_id"]
        
        # Consulta a nota importada
        detail_response = client.get(f"/fiscal-notes/{note_id}")
        assert detail_response.status_code == 200
        
        note_details = detail_response.json()
        assert note_details["id"] == note_id
        assert note_details["seller_name"] == "LOJA EXEMPLO LTDA"
        assert note_details["total_amount"] == 38.5
        assert len(note_details["items"]) == 2
        
        # Verifica os itens
        items = sorted(note_details["items"], key=lambda x: x["product_name"])
        assert items[0]["product_name"] == "ARROZ TIPO 1 KG"
        assert items[0]["quantity"] == 2.0
        assert items[0]["unit_price"] == 15.0
        assert items[0]["total_price"] == 30.0
        
        assert items[1]["product_name"] == "FEIJAO PRETO 1KG"
        assert items[1]["quantity"] == 1.0
        assert items[1]["unit_price"] == 8.5
        assert items[1]["total_price"] == 8.5
        
        # Consulta usando o endpoint de listagem
        list_response = client.get("/fiscal-notes")
        assert list_response.status_code == 200
        notes_list = list_response.json()
        
        found_note = next((note for note in notes_list if note["id"] == note_id), None)
        assert found_note is not None
        assert found_note["seller_name"] == "LOJA EXEMPLO LTDA"
        assert found_note["total_amount"] == 38.5
        assert len(found_note["items"]) == 2
        
    finally:
        # Limpa o arquivo temporário
        temp_file_path.unlink()
        # Remove o banco de teste
        Path("test_e2e.db").unlink(missing_ok=True)


if __name__ == "__main__":
    test_e2e_xml_import_and_query()
    print("✅ Teste E2E de importação e consulta realizado com sucesso!")