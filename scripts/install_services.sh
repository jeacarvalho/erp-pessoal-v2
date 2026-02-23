#!/bin/bash
# Script de instalação dos serviços do ERP Pessoal

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEMD_DIR="$HOME/.config/systemd/user"

echo "=========================================="
echo "🚀 Instalando serviços do ERP Pessoal"
echo "=========================================="

# Criar diretório systemd do usuário
mkdir -p "$SYSTEMD_DIR"

# Copiar serviços
cp "$SCRIPT_DIR/erp-backend.service" "$SYSTEMD_DIR/"
cp "$SCRIPT_DIR/erp-web.service" "$SYSTEMD_DIR/"

# Recarregar systemd
systemctl --user daemon-reload

echo ""
echo "✅ Serviços instalados!"
echo ""
echo "Para gerenciar os serviços:"
echo "  Iniciar:    systemctl --user start erp-backend erp-web"
echo "  Parar:      systemctl --user stop erp-backend erp-web"
echo "  Status:     systemctl --user status erp-backend erp-web"
echo "  Reiniciar:  systemctl --user restart erp-backend erp-web"
echo ""
echo "Para iniciar automaticamente ao ligar:"
echo "  systemctl --user enable erp-backend erp-web"
echo ""
echo "Para testar agora (sem reiniciar):"
echo "  systemctl --user start erp-backend erp-web"
