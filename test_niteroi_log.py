#!/usr/bin/env python3
"""
Test script to verify the logging functionality when an item has the name "NITEROI".
"""

import sys
import os
sys.path.insert(0, '/workspace/backend')

from backend.app.services.scraper_handler import DefaultSefazAdapter
from bs4 import BeautifulSoup
import logging

# Set up logging to see the warning messages
logging.basicConfig(level=logging.WARNING, format='%(levelname)s:%(name)s:%(message)s')

# Create a modified HTML where the first item would be incorrectly parsed as "NITEROI"
# This simulates a case where the txtTit span contains "NITEROI" instead of the product name
html_with_niteroi = '''<?xml version="1.0" encoding="ISO-8859-1"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="pt-br" lang="pt-br">
<head>
<title>Test NFC-e</title>
</head>
<body>
<div id="conteudo">
<table data-filter="true" id="tabResult" cellspacing="0" cellpadding="0" align="center" border="0">
<tr id="Item + 1">
<td valign="top"><span class="txtTit">NITEROI</span><span class="RCod">(C&oacute;digo: 12345)</span>
<br>
<span class="Rqtd"><strong>Qtde.:</strong>1</span><span class="RUN"><strong>UN: </strong>UN</span><span class="RvlUnit"><strong>Vl. Unit.:</strong>10,00</span></td><td class="txtTit noWrap" valign="top" align="right">Vl. Total<br><span class="valor">10,00</span></td>
</tr>
</table>
</div>
</body>
</html>'''

def test_niteroi_logging():
    """Test that when an item has the name 'NITEROI', it gets properly logged."""
    adapter = DefaultSefazAdapter()
    soup = BeautifulSoup(html_with_niteroi, "html.parser")
    
    print("Testing NITEROI logging functionality...")
    
    # Extract items using the method with logging
    items = adapter._extract_items(soup)
    
    print(f"Number of items extracted: {len(items)}")
    
    if len(items) > 0:
        print(f"First item name: '{items[0].name}'")
        print("Check above for any warning logs about 'NITEROI' being found.")
    else:
        print("No items were extracted")

if __name__ == "__main__":
    test_niteroi_logging()