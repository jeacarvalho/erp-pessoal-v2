#!/bin/bash
# Script simplificado: Backend + Web local + Build APK
# Mobile acessa via IP da rede local

set -e

PROJECT_DIR="/home/s015533607/Documentos/desenv/erp-pessoal-v2"
BACKEND_DIR="$PROJECT_DIR/backend"
WEB_DIR="$PROJECT_DIR/web"
MOBILE_DIR="$PROJECT_DIR/mobile"

echo "=========================================="
echo "🚀 ERP Pessoal - Setup Local"
echo "=========================================="
echo ""

# Pega IP local
LOCAL_IP=$(hostname -I | awk '{print $1}')
echo "📍 IP Local: $LOCAL_IP"
echo ""

# Atualiza mobile/.env com IP local
echo "VITE_API_URL=http://${LOCAL_IP}:8000" > "$MOBILE_DIR/.env"
echo "✅ mobile/.env atualizado"
echo ""

echo "📦 1. Iniciando Backend (porta 8000)..."
cd "$BACKEND_DIR"
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "   Backend: http://localhost:8000"
echo "   Backend: http://${LOCAL_IP}:8000"
echo ""

echo "📦 2. Iniciando Web Streamlit (porta 8501)..."
cd "$WEB_DIR"
BACKEND_URL="http://localhost:8000" streamlit run app_streamlit.py --server.port 8501 --server.address 0.0.0.0 &
WEB_PID=$!
echo "   Web: http://localhost:8501"
echo "   Web: http://${LOCAL_IP}:8501"
echo ""

echo "📱 3. Buildando Mobile APK..."
export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
cd "$MOBILE_DIR"
npm run build
npx cap sync android
cd android
./gradlew assembleDebug

APK_PATH="$MOBILE_DIR/android/app/build/outputs/apk/debug/app-debug.apk"

echo ""
echo "=========================================="
echo "✅ TUDO PRONTO!"
echo "=========================================="
echo ""
echo "🔗 Acesse localmente:"
echo "   Backend: http://localhost:8000"
echo "   Web:     http://localhost:8501"
echo ""
echo "📱 Para outros dispositivos (mesma rede WiFi):"
echo "   Backend: http://${LOCAL_IP}:8000"
echo "   Web:     http://${LOCAL_IP}:8501"
echo ""
echo "📦 APK Gerado:"
echo "   $APK_PATH"
echo ""
echo "💡 Para instalar no Android:"
echo "   adb install \"$APK_PATH\""
echo ""
echo "🛑 Pressione Ctrl+C para encerrar"
echo ""

wait
