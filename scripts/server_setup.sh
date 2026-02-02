#!/bin/bash
#
# Gatekeeper NAS - Server Setup Script
# Run this script on the Ubuntu Server (El Almacen)
#
# Usage: sudo bash server_setup.sh
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration - MODIFY THESE VALUES
DATA_DISK="/dev/sdb1"           # Disk partition for user data
DATA_MOUNT="/datos"             # Mount point for data
GATEKEEPER_USER="gatekeeper"    # User for SSH access from Pi
RASPBERRY_IP="192.168.10.X"     # IP of Raspberry Pi (change this!)
NETWORK_INTERFACE="enp0s3"      # Network interface (check with: ip link)

echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         GATEKEEPER NAS - SERVER SETUP                     ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: Este script debe ejecutarse como root (sudo)${NC}"
    exit 1
fi

# 1. Update system
echo -e "${YELLOW}[1/8] Actualizando sistema...${NC}"
apt update && apt upgrade -y

# 2. Install required packages
echo -e "${YELLOW}[2/8] Instalando paquetes necesarios...${NC}"
apt install -y nfs-kernel-server quota quotatool ethtool openssh-server

# 3. Create data mount point
echo -e "${YELLOW}[3/8] Configurando punto de montaje...${NC}"
mkdir -p $DATA_MOUNT

# Check if disk exists
if [ -b "$DATA_DISK" ]; then
    # Add to fstab if not already there
    if ! grep -q "$DATA_DISK" /etc/fstab; then
        echo "$DATA_DISK $DATA_MOUNT ext4 defaults,usrquota,grpquota 0 2" >> /etc/fstab
        echo -e "${GREEN}Disco agregado a /etc/fstab${NC}"
    fi

    # Mount the disk
    mount -a
    echo -e "${GREEN}Disco montado en $DATA_MOUNT${NC}"
else
    echo -e "${YELLOW}ADVERTENCIA: Disco $DATA_DISK no encontrado.${NC}"
    echo -e "${YELLOW}Configura manualmente /etc/fstab con tu disco de datos.${NC}"
    echo -e "${YELLOW}Ejemplo: /dev/sdX1 $DATA_MOUNT ext4 defaults,usrquota,grpquota 0 2${NC}"
fi

# 4. Enable and configure quotas
echo -e "${YELLOW}[4/8] Configurando sistema de cuotas...${NC}"
if mountpoint -q $DATA_MOUNT; then
    # Create quota files
    quotacheck -cugm $DATA_MOUNT 2>/dev/null || true
    quotaon $DATA_MOUNT 2>/dev/null || true
    echo -e "${GREEN}Cuotas habilitadas en $DATA_MOUNT${NC}"
else
    echo -e "${YELLOW}El punto de montaje no esta activo. Configura cuotas despues de montar el disco.${NC}"
fi

# 5. Configure NFS exports
echo -e "${YELLOW}[5/8] Configurando NFS...${NC}"
NFS_EXPORT="$DATA_MOUNT $RASPBERRY_IP(rw,sync,no_subtree_check,no_root_squash)"

if ! grep -q "$DATA_MOUNT" /etc/exports; then
    echo "$NFS_EXPORT" >> /etc/exports
    echo -e "${GREEN}Export NFS agregado${NC}"
fi

# Restart NFS
exportfs -ra
systemctl restart nfs-kernel-server
systemctl enable nfs-kernel-server

# 6. Create gatekeeper user for SSH
echo -e "${YELLOW}[6/8] Creando usuario gatekeeper...${NC}"
if ! id "$GATEKEEPER_USER" &>/dev/null; then
    useradd -m -s /bin/bash $GATEKEEPER_USER
    echo -e "${GREEN}Usuario $GATEKEEPER_USER creado${NC}"
else
    echo -e "${YELLOW}Usuario $GATEKEEPER_USER ya existe${NC}"
fi

# Create .ssh directory
mkdir -p /home/$GATEKEEPER_USER/.ssh
chmod 700 /home/$GATEKEEPER_USER/.ssh
touch /home/$GATEKEEPER_USER/.ssh/authorized_keys
chmod 600 /home/$GATEKEEPER_USER/.ssh/authorized_keys
chown -R $GATEKEEPER_USER:$GATEKEEPER_USER /home/$GATEKEEPER_USER/.ssh

# 7. Configure sudo for gatekeeper
echo -e "${YELLOW}[7/8] Configurando permisos sudo...${NC}"
SUDOERS_FILE="/etc/sudoers.d/gatekeeper"
cat > $SUDOERS_FILE << 'EOF'
# Gatekeeper NAS - Sudo permissions
# Allow gatekeeper user to run specific commands without password

gatekeeper ALL=(ALL) NOPASSWD: /sbin/poweroff
gatekeeper ALL=(ALL) NOPASSWD: /usr/sbin/useradd *
gatekeeper ALL=(ALL) NOPASSWD: /usr/sbin/userdel *
gatekeeper ALL=(ALL) NOPASSWD: /usr/sbin/setquota *
gatekeeper ALL=(ALL) NOPASSWD: /usr/bin/mkdir -p /datos/*
gatekeeper ALL=(ALL) NOPASSWD: /bin/chown *
gatekeeper ALL=(ALL) NOPASSWD: /bin/chmod *
gatekeeper ALL=(ALL) NOPASSWD: /bin/rm -rf /datos/*
EOF

chmod 440 $SUDOERS_FILE
echo -e "${GREEN}Permisos sudo configurados${NC}"

# 8. Configure Wake-on-LAN
echo -e "${YELLOW}[8/8] Configurando Wake-on-LAN...${NC}"

# Check current WoL status
WOL_STATUS=$(ethtool $NETWORK_INTERFACE 2>/dev/null | grep "Wake-on" | head -1 || echo "")

if [ -n "$WOL_STATUS" ]; then
    # Enable WoL
    ethtool -s $NETWORK_INTERFACE wol g

    # Create systemd service to enable WoL on boot
    cat > /etc/systemd/system/wol.service << EOF
[Unit]
Description=Enable Wake-on-LAN
After=network.target

[Service]
Type=oneshot
ExecStart=/sbin/ethtool -s $NETWORK_INTERFACE wol g

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable wol.service
    echo -e "${GREEN}Wake-on-LAN configurado en $NETWORK_INTERFACE${NC}"
else
    echo -e "${YELLOW}No se pudo detectar WoL en $NETWORK_INTERFACE${NC}"
    echo -e "${YELLOW}Verifica que WoL este habilitado en la BIOS${NC}"
fi

# Summary
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              CONFIGURACION COMPLETADA                      ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Resumen:"
echo -e "  - NFS Export: $DATA_MOUNT -> $RASPBERRY_IP"
echo -e "  - Usuario SSH: $GATEKEEPER_USER"
echo -e "  - Wake-on-LAN: Habilitado en $NETWORK_INTERFACE"
echo ""
echo -e "${YELLOW}PASOS SIGUIENTES:${NC}"
echo -e "1. Copia la llave SSH publica de la Raspberry Pi a:"
echo -e "   /home/$GATEKEEPER_USER/.ssh/authorized_keys"
echo ""
echo -e "2. Verifica que Wake-on-LAN este habilitado en la BIOS del servidor"
echo ""
echo -e "3. Configura IP estatica en /etc/netplan/ si no lo has hecho"
echo ""
echo -e "4. Reinicia el servidor para aplicar todos los cambios"
echo ""
