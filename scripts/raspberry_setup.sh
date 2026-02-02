#!/bin/bash
#
# Gatekeeper NAS - Raspberry Pi Setup Script
# Run this script on the Raspberry Pi (El Gatekeeper)
#
# Usage: sudo bash raspberry_setup.sh
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration - MODIFY THESE VALUES
SERVER_IP="192.168.10.14"
NFS_MOUNT="/mnt/servidor"
APP_DIR="/opt/gatekeeper"
APP_USER="pi"  # User that will run the app

echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       GATEKEEPER NAS - RASPBERRY PI SETUP                 ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: Este script debe ejecutarse como root (sudo)${NC}"
    exit 1
fi

# 1. Update system
echo -e "${YELLOW}[1/6] Actualizando sistema...${NC}"
apt update && apt upgrade -y

# 2. Install required packages
echo -e "${YELLOW}[2/6] Instalando paquetes...${NC}"
apt install -y python3-pip python3-venv nfs-common wakeonlan

# 3. Create NFS mount point
echo -e "${YELLOW}[3/6] Configurando punto de montaje NFS...${NC}"
mkdir -p $NFS_MOUNT

# Add to fstab (but don't auto-mount - app will handle this)
if ! grep -q "$SERVER_IP" /etc/fstab; then
    echo "# Gatekeeper NAS - NFS mount (managed by app, not auto-mounted)" >> /etc/fstab
    echo "# $SERVER_IP:/datos $NFS_MOUNT nfs soft,timeo=10,noauto 0 0" >> /etc/fstab
fi

# 4. Generate SSH key
echo -e "${YELLOW}[4/6] Configurando SSH...${NC}"
SSH_KEY="/home/$APP_USER/.ssh/id_rsa"

if [ ! -f "$SSH_KEY" ]; then
    sudo -u $APP_USER ssh-keygen -t rsa -b 4096 -f $SSH_KEY -N ""
    echo -e "${GREEN}Llave SSH generada${NC}"
else
    echo -e "${YELLOW}Llave SSH ya existe${NC}"
fi

# 5. Create application directory
echo -e "${YELLOW}[5/6] Preparando directorio de aplicacion...${NC}"
mkdir -p $APP_DIR
chown $APP_USER:$APP_USER $APP_DIR

# 6. Create systemd service
echo -e "${YELLOW}[6/6] Creando servicio systemd...${NC}"
cat > /etc/systemd/system/gatekeeper.service << EOF
[Unit]
Description=Gatekeeper NAS Web Application
After=network.target

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/gunicorn -w 2 -b 0.0.0.0:5000 'app:create_app()'
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload

# Summary
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              CONFIGURACION COMPLETADA                      ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Resumen:"
echo -e "  - NFS Mount Point: $NFS_MOUNT"
echo -e "  - App Directory: $APP_DIR"
echo -e "  - Servicio: gatekeeper.service"
echo ""
echo -e "${YELLOW}PASOS SIGUIENTES:${NC}"
echo ""
echo -e "1. Copia la llave publica al servidor:"
echo -e "   ${GREEN}ssh-copy-id gatekeeper@$SERVER_IP${NC}"
echo ""
echo -e "2. Copia los archivos de la aplicacion a $APP_DIR"
echo ""
echo -e "3. Crea el entorno virtual e instala dependencias:"
echo -e "   ${GREEN}cd $APP_DIR${NC}"
echo -e "   ${GREEN}python3 -m venv venv${NC}"
echo -e "   ${GREEN}source venv/bin/activate${NC}"
echo -e "   ${GREEN}pip install -r requirements.txt gunicorn${NC}"
echo ""
echo -e "4. Configura el archivo .env con tus valores"
echo ""
echo -e "5. Inicia el servicio:"
echo -e "   ${GREEN}sudo systemctl enable gatekeeper${NC}"
echo -e "   ${GREEN}sudo systemctl start gatekeeper${NC}"
echo ""
echo -e "6. Verifica que funciona:"
echo -e "   ${GREEN}sudo systemctl status gatekeeper${NC}"
echo ""
echo -e "La aplicacion estara disponible en: http://$(hostname -I | awk '{print $1}'):5000"
echo ""
