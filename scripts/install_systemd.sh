#!/bin/bash
# Script de instalação dos serviços do ERP Pessoal (system-wide)
# Execute como root: sudo ./install_systemd.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "🚀 Instalando serviços do ERP Pessoal"
echo "=========================================="

if [ "$EUID" -ne 0 ]; then
    echo "❌ Execute como root: sudo $0"
    exit 1
fi

# Copiar serviços para systemd
cp "$SCRIPT_DIR/erp-backend-systemd.service" /etc/systemd/system/
cp "$SCRIPT_DIR/erp-web-systemd.service" /etc/systemd/system/

# Recarregar systemd
systemctl daemon-reload

echo ""
echo "✅ Serviços instalados!"
echo ""
echo "Para gerenciar os serviços:"
echo "  Iniciar:    sudo systemctl start erp-backend erp-web"
echo "  Parar:      sudo systemctl stop erp-backend erp-web"
echo "  Status:     sudo systemctl status erp-backend erp-web"
echo "  Reiniciar:  sudo systemctl restart erp-backend erp-web"
echo ""
echo "Para iniciar automaticamente ao ligar:"
echo "  sudo systemctl enable erp-backend erp-web"
echo ""
echo "Para testar agora (sem reiniciar):"
echo "  sudo systemctl start erp-backend erp-web"
