#!/usr/bin/env python3
"""
Test script to verify the fix for the RJSefazNFCeAdapter item extraction issue.
"""

import sys
import os
sys.path.insert(0, '/workspace/backend')

from backend.app.services.scraper_handler import DefaultSefazAdapter
from bs4 import BeautifulSoup

# HTML content provided in the issue
html_content = '''<?xml version="1.0" encoding="ISO-8859-1"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="pt-br" lang="pt-br"><head id="j_idt2">
<script type="text/javascript">
(function(){
window["loaderConfig"] = "/TSPD/?type=21";
})();

</script>

<script type="text/javascript" src="/TSPD/?type=18"></script>

<meta http-equiv="X-UA-Compatible" content="IE=9, IE=edge" /> 
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name="format-detection" content="telephone=no" />
<meta name="robots" content="noindex" />
<meta name="googlebot" content="noindex" />
<title>Consulta QRCode NFC-e</title>
	<script type="text/javascript" src="https://code.jquery.com/jquery-1.9.1.js  "></script><script type="text/javascript" src="/consultaNFCe/javax.faces.resource/index.js.faces?ln=js"></script><script type="text/javascript" src="/consultaNFCe/javax.faces.resource/jquery.mobile-1.4.5.min.js.faces?ln=js"></script>
	<script async="true" src="https://www.googletagmanager.com/gtag/js?id=G-7JK4931RGY"></script><link type="text/css" rel="stylesheet" href="/consultaNFCe/javax.faces.resource/jquery.mobile-1.4.5.min.css.faces?ln=css" /><link type="text/css" rel="stylesheet" href="/consultaNFCe/javax.faces.resource/nfceMob.css.faces?ln=css" /><link type="text/css" rel="stylesheet" href="/consultaNFCe/javax.faces.resource/nfceMob_ie.css.faces?ln=css" /></head><body><div xmlns:r="http://www.serpro.gov.br/nfe/remessanfe.xsd" xmlns:chave="http://exslt.org/chaveacesso" xmlns:n="http://www.portalfiscal.inf.br/nfe" data-role="header">
<h1 class="tit">
<img alt="NFC-e" height="64" width="112" src="../resources/images/logoNFCe.png"><p>DOCUMENTO AUXILIAR DA NOTA FISCAL DE CONSUMIDOR ELETR&Ocirc;NICA</p>
<p></p>
</h1>
</div><div data-role="content">
<div id="conteudo">
<div id="avisos"></div>
<div class="txtCenter">
<div class="txtTopo" id="u20">PRECO DE POPULAR ITAIPU LTDA</div>
<div class="text">
								CNPJ:
								27.207.407/0001-40</div>
<div class="text">ESTRADA FRANCISCO DA CRUZ NUNES
							,
							2376
							,
							LOJA 101
							,
							ITAIPU
							,
							NITEROI
							,
							RJ</div>
</div>
<table data-filter="true" id="tabResult" cellspacing="0" cellpadding="0" align="center" border="0">
<tr id="Item + 1">
<td valign="top"><span class="txtTit">IMEDIA SEM AMONIA 6U LOURO ESCURO UNIVERSAL</span><span class="RCod">
										(C&oacute;digo:
										0393691
										)
									</span>
<br>
<span class="Rqtd"><strong>Qtde.:</strong>1</span><span class="RUN"><strong>UN: </strong>UN</span><span class="RvlUnit"><strong>Vl. Unit.:</strong>
										&nbsp;
										34,79</span></td><td class="txtTit noWrap" valign="top" align="right">
									Vl. Total
									<br>
<span class="valor">34,79</span></td>
</tr>
<tr id="Item + 2">
<td valign="top"><span class="txtTit">TELE-ENTREGA</span><span class="RCod">
										(C&oacute;digo:
										0438646
										)
									</span>
<br>
<span class="Rqtd"><strong>Qtde.:</strong>1</span><span class="RUN"><strong>UN: </strong>UN</span><span class="RvlUnit"><strong>Vl. Unit.:</strong>
										&nbsp;
										4,99</span></td><td class="txtTit noWrap" valign="top" align="right">
									Vl. Total
									<br>
<span class="valor">4,99</span></td>
</tr>
</table>
<div class="txtRight" id="totalNota">
<div id="linhaTotal">
<label>Qtd. total de itens:</label><span class="totalNumb">2</span>
</div>
<div id="linhaTotal">
<label>Valor total R$:</label><span class="totalNumb">39,78</span>
</div>
<div id="linhaTotal">
<label>Descontos R$:</label><span class="totalNumb">5,22</span>
</div>
<div class="linhaShade" id="linhaTotal">
<label>Valor a pagar R$:</label><span class="totalNumb txtMax">34,56</span>
</div>
<div id="linhaForma">
<label>Forma de pagamento:</label><span class="totalNumb txtTitR">Valor pago R$:</span>
</div>
<div id="linhaTotal">
<label class="tx">
											Cart&atilde;o de Cr&eacute;dito
										</label><span class="totalNumb">34,56</span>
</div>
<div id="linhaTotal">
<label class="tx">Troco </label><span class="totalNumb">0,00</span>
</div>
</div>
</div>
<div class="txtCenter" id="infos">
<div data-collapsed="false" data-expanded-icon="carat-u" data-collapsed-icon="carat-d" data-role="collapsible">
<h4>Informa&ccedil;&otilde;es gerais da Nota</h4>
<ul data-inset="false" data-role="listview">
<li>
<strong>EMISS&Atilde;O NORMAL</strong>
<br>
<br>
<strong>N&uacute;mero: </strong>297945<strong> S&eacute;rie: </strong>1<strong> Emiss&atilde;o: </strong>12/02/2026 17:21:02-03:00
								- Via Consumidor 2
								<br>
<br>
<strong>Protocolo de Autoriza&ccedil;&atilde;o: </strong>233260361876136       12/02/2026 
        &agrave;s
      17:22:58-03:00<br>
<br>
<strong>
										Ambiente de Produ&ccedil;&atilde;o -
									
									Vers&atilde;o XML:
									4.00
									- Vers&atilde;o XSLT: 2.07
								</strong>
</li>
</ul>
</div>
<div data-collapsed="false" data-expanded-icon="carat-u" data-collapsed-icon="carat-d" data-role="collapsible">
<h4>Chave de acesso</h4>
<ul data-inset="false" data-role="listview">
<li>
								Consulte pela Chave de Acesso em
								
								www.fazenda.rj.gov.br/nfce/consulta<br>
<br>
<strong>Chave de acesso:</strong>
<br>
<span class="chave">3326 0227 2074 0700 0140 6500 1000 2979 4511 0297 9451</span>
</li>
</ul>
</div>
<div data-collapsed="false" data-expanded-icon="carat-u" data-collapsed-icon="carat-d" data-role="collapsible">
<h4>Consumidor</h4>
<ul data-inset="false" data-role="listview">
<li>
<strong>CPF: </strong>974.115.907-20</li>
<li>
<strong>Nome: </strong>ANA CARVALHO</li>
<li>
<strong>Logradouro: </strong>RUA JORNALISTA PAULO FRANCIS CASA 33
									,
									33
									,
									
									,
									CAMBOINHAS
									,
									NITEROI
									,
									RJ</li>
</ul>
</div>
</div>
</div>
			
		<!-- versao:  -->
		<!--  --></body>
	<script type="text/javascript">		
		$(function(){				
			$('#linkMsg').click(function(event) {  //on click 
				$('#mensagem').toggle();
	    	});
		});

		window.dataLayer = window.dataLayer || [];
	  	function gtag(){dataLayer.push(arguments);}
	  	gtag('js', new Date());
	
	  	gtag('config', 'G-7JK4931RGY');
		
	</script>
</html>'''

def test_item_extraction():
    """Test that the first item is correctly extracted as 'IMEDIA SEM AMONIA 6U LOURO ESCURO UNIVERSAL' and not 'NITEROI'."""
    adapter = DefaultSefazAdapter()
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Extract items using the fixed method
    items = adapter._extract_items(soup)
    
    print(f"Number of items extracted: {len(items)}")
    
    for i, item in enumerate(items):
        print(f"Item {i+1}:")
        print(f"  Name: '{item.name}'")
        print(f"  Quantity: {item.quantity}")
        print(f"  Unit: {item.unit}")
        print(f"  Unit Price: {item.unit_price}")
        print(f"  Total Price: {item.total_price}")
        print()
    
    # Verify the first item has the correct name
    if len(items) > 0:
        first_item_name = items[0].name
        print(f"First item name: '{first_item_name}'")
        
        if first_item_name == "IMEDIA SEM AMONIA 6U LOURO ESCURO UNIVERSAL":
            print("SUCCESS: First item correctly extracted as 'IMEDIA SEM AMONIA 6U LOURO ESCURO UNIVERSAL'")
            return True
        elif first_item_name.lower() == "niteroi":
            print("FAILURE: First item incorrectly extracted as 'NITEROI'")
            return False
        else:
            print(f"WARNING: First item extracted as '{first_item_name}', expected 'IMEDIA SEM AMONIA 6U LOURO ESCURO UNIVERSAL'")
            return False
    else:
        print("FAILURE: No items were extracted")
        return False

if __name__ == "__main__":
    success = test_item_extraction()
    if success:
        print("\nThe fix is working correctly!")
    else:
        print("\nThe fix did not resolve the issue.")
        sys.exit(1)