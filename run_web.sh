#!/bin/bash
# Script para executar o frontend web do ERP Pessoal

echo "🚀 Iniciando frontend do ERP Pessoal..."
echo ""
echo "⚠️  Certifique-se de que o backend está rodando em http://localhost:8000"
echo ""

cd "$(dirname "$0")/web" || exit 1

# Verifica se as dependências estão instaladas
if ! python3 -c "import flet" 2>/dev/null; then
    echo "📦 Instalando dependências..."
    pip install -r requirements.txt
fi

echo "✨ Abrindo interface..."
python3 -m app.main
