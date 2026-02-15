from __future__ import annotations
import pytest
from backend.app.services.xml_handler import XMLProcessor

@pytest.fixture
def processor():
    return XMLProcessor()

def test_parse_psyllium_velez(processor):
    """Valida o XML da ARG (Psyllium) com estrutura XML válida e namespaces."""
    # XML formatado corretamente para o parser não quebrar na coluna 9
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
        <NFe>
            <infNFe Id="NFe35260223692529000119550020003636811294702620">
                <emit><xNome>A R G</xNome></emit>
                <ide><dhEmi>2026-02-13T16:09:54-03:00</dhEmi></ide>
                <total><ICMSTot><vNF>17.90</vNF></ICMSTot></total>
                <det nItem="1">
                    <prod>
                        <cEAN>7899936402322</cEAN>
                        <xProd>Psyllium Velez 200g Puro Rico Em Fibras 100% Natural</xProd>
                        <qCom>1.0000</qCom>
                        <vUnCom>17.9000</vUnCom>
                        <vProd>17.90</vProd>
                    </prod>
                </det>
            </infNFe>
        </NFe>
    </nfeProc>"""
    
    parsed = processor.parse(xml_content.encode('utf-8'))
    
    # Validações dos dados extraídos do XML do Psyllium [cite: 172]
    assert parsed.seller_name == "A R G" [cite: 172]
    assert parsed.access_key == "35260223692529000119550020003636811294702620" [cite: 172]
    assert parsed.items[0].name == "Psyllium Velez 200g Puro Rico Em Fibras 100% Natural" [cite: 172]
    assert parsed.items[0].product_ean == "7899936402322" [cite: 172]
    assert float(parsed.items[0].unit_price) == 17.90 [cite: 172]

def test_parse_barilla_with_newline_cleanup(processor):
    """Garante que o nome 'EBAZAR.COM.BR.\\nLTDA' seja limpo corretamente."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
        <NFe><infNFe Id="NFe35260203007331021220550020099992201486087786">
            <emit><xNome>EBAZAR.COM.BR.\\nLTDA</xNome></emit>
            <ide><dhEmi>2026-02-13T16:09:53-03:00</dhEmi></ide>
            <total><ICMSTot><vNF>8.38</vNF></ICMSTot></total>
            <det nItem="1"><prod>
                <cEAN>7898951850064</cEAN>
                <xProd>Macarrao com Ovos Espaguete 8 Barilla Pacote 500g</xProd>
                <qCom>2.0000</qCom>
                <vUnCom>4.1900</vUnCom>
                <vProd>8.38</vProd>
            </prod></det>
        </infNFe></NFe>
    </nfeProc>"""
    
    parsed = processor.parse(xml_content.encode('utf-8'))
    
    # Valida a limpeza da quebra de linha no vendedor [cite: 178]
    assert "EBAZAR.COM.BR." in parsed.seller_name [cite: 178]
    assert "\\n" not in parsed.seller_name [cite: 178]
    assert parsed.items[0].product_ean == "7898951850064" [cite: 178]

def test_parse_eisenbahn_bulk_quantity(processor):
    """Valida a extração de quantidades e preços da Eisenbahn."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
        <NFe><infNFe Id="NFe35260247508411234300553100282724151861019983">
            <emit><xNome>COMPANHIA BRASILEIRA DE DISTRIBUICAO</xNome></emit>
            <ide><dhEmi>2026-02-13T16:09:54-03:00</dhEmi></ide>
            <total><ICMSTot><vNF>111.24</vNF></ICMSTot></total>
            <det nItem="1"><prod>
                <cEAN>7898367983790</cEAN>
                <xProd>CERV BRASIL EISENBAHN SLEEK 350ML</xProd>
                <qCom>36.0000</qCom>
                <vUnCom>3.0900</vUnCom>
                <vProd>111.24</vProd>
            </prod></det>
        </infNFe></NFe>
    </nfeProc>"""
    
    parsed = processor.parse(xml_content.encode('utf-8'))
    
    # Valida dados da Eisenbahn [cite: 183]
    assert float(parsed.items[0].quantity) == 36.0 [cite: 183]
    assert float(parsed.items[0].unit_price) == 3.09 [cite: 183]
    assert parsed.items[0].product_ean == "7898367983790" [cite: 183]