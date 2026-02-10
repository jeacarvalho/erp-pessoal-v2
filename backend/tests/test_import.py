from __future__ import annotations

from backend.app.services.xml_handler import XMLProcessor


def test_xml_processor_parses_quantity_and_unit_price_separately() -> None:
    """Garante que o XMLProcessor separa corretamente quantidade e preço unitário."""

    xml_content = """
    <NFe>
      <infNFe Id="NFe123">
        <emit>
          <xNome>Supermercado Exemplo</xNome>
        </emit>
        <det nItem="1">
          <prod>
            <xProd>Arroz 5kg</xProd>
            <qCom>2.0000</qCom>
            <uCom>UN</uCom>
            <vUnCom>10.00</vUnCom>
            <vProd>20.00</vProd>
          </prod>
        </det>
      </infNFe>
      <total>
        <ICMSTot>
          <vNF>20.00</vNF>
        </ICMSTot>
      </total>
    </NFe>
    """.strip()

    processor = XMLProcessor()
    parsed = processor.parse(xml_content)

    assert parsed.total_amount == 20.0
    assert len(parsed.items) == 1

    item = parsed.items[0]
    assert item.name == "Arroz 5kg"
    assert item.quantity == 2.0
    assert item.unit == "UN"
    assert item.unit_price == 10.0
    assert item.total_price == 20.0

