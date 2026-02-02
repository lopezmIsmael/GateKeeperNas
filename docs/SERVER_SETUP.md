# Configuracion del Servidor Ubuntu (El Almacen)

Esta guia detalla como configurar el servidor Ubuntu que almacenara los datos de los usuarios.

## Requisitos Previos

- Ubuntu Server 22.04 LTS o superior
- Disco duro dedicado para datos de usuarios
- Conexion de red cableada
- Wake-on-LAN soportado por la placa base

## 1. Configuracion de Red

### IP Estatica

Edita el archivo de configuracion de netplan:

```bash
sudo nano /etc/netplan/00-installer-config.yaml
```

Contenido:

```yaml
network:
  version: 2
  ethernets:
    enp0s3:  # Cambia por tu interfaz (ver: ip link)
      dhcp4: no
      addresses:
        - 192.168.10.14/24
      gateway4: 192.168.10.1
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
```

Aplica la configuracion:

```bash
sudo netplan apply
```

## 2. Wake-on-LAN

### Verificar en BIOS

1. Reinicia el servidor y entra a la BIOS
2. Busca opciones como:
   - "Wake on LAN"
   - "Power On by PCI-E"
   - "Wake on PME"
3. Habilitalas

### Verificar en Linux

```bash
# Instalar ethtool
sudo apt install ethtool

# Ver estado de WoL
sudo ethtool enp0s3 | grep Wake-on

# Habilitar WoL
sudo ethtool -s enp0s3 wol g
```

Para que persista despues de reiniciar, crea un servicio systemd:

```bash
sudo nano /etc/systemd/system/wol.service
```

```ini
[Unit]
Description=Enable Wake-on-LAN
After=network.target

[Service]
Type=oneshot
ExecStart=/sbin/ethtool -s enp0s3 wol g

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable wol.service
```

## 3. Disco de Datos

### Identificar el disco

```bash
lsblk
# o
sudo fdisk -l
```

### Formatear (si es nuevo)

```bash
# Crear particion
sudo fdisk /dev/sdb
# Comandos: n (nueva), p (primaria), Enter (defaults), w (escribir)

# Formatear como ext4
sudo mkfs.ext4 /dev/sdb1
```

### Montar con soporte de cuotas

```bash
# Crear punto de montaje
sudo mkdir /datos

# Editar fstab
sudo nano /etc/fstab
```

Agrega la linea:

```
/dev/sdb1  /datos  ext4  defaults,usrquota,grpquota  0  2
```

```bash
# Montar
sudo mount -a

# Verificar
df -h /datos
```

## 4. Sistema de Cuotas

```bash
# Instalar herramientas
sudo apt install quota quotatool

# Inicializar cuotas
sudo quotacheck -cugm /datos

# Habilitar cuotas
sudo quotaon /datos

# Verificar
sudo repquota /datos
```

### Comandos utiles de cuotas

```bash
# Ver cuota de un usuario
quota -u nombreusuario

# Establecer cuota (500GB soft y hard)
sudo setquota -u nombreusuario 524288000 524288000 0 0 /datos

# Ver todas las cuotas
sudo repquota -a
```

## 5. NFS (Network File System)

```bash
# Instalar servidor NFS
sudo apt install nfs-kernel-server

# Configurar exports
sudo nano /etc/exports
```

Agrega:

```
/datos  192.168.10.0/24(rw,sync,no_subtree_check,no_root_squash)
```

Nota: Ajusta la IP/mascara segun tu red.

```bash
# Aplicar cambios
sudo exportfs -ra

# Reiniciar servicio
sudo systemctl restart nfs-kernel-server
sudo systemctl enable nfs-kernel-server

# Verificar exports
showmount -e localhost
```

## 6. Usuario SSH para la Raspberry Pi

```bash
# Crear usuario
sudo useradd -m -s /bin/bash gatekeeper

# Crear directorio SSH
sudo mkdir /home/gatekeeper/.ssh
sudo chmod 700 /home/gatekeeper/.ssh
sudo touch /home/gatekeeper/.ssh/authorized_keys
sudo chmod 600 /home/gatekeeper/.ssh/authorized_keys
sudo chown -R gatekeeper:gatekeeper /home/gatekeeper/.ssh
```

### Configurar sudo sin contrasena

```bash
sudo nano /etc/sudoers.d/gatekeeper
```

```
gatekeeper ALL=(ALL) NOPASSWD: /sbin/poweroff
gatekeeper ALL=(ALL) NOPASSWD: /usr/sbin/useradd *
gatekeeper ALL=(ALL) NOPASSWD: /usr/sbin/userdel *
gatekeeper ALL=(ALL) NOPASSWD: /usr/sbin/setquota *
gatekeeper ALL=(ALL) NOPASSWD: /usr/bin/mkdir -p /datos/*
gatekeeper ALL=(ALL) NOPASSWD: /bin/chown *
gatekeeper ALL=(ALL) NOPASSWD: /bin/chmod *
gatekeeper ALL=(ALL) NOPASSWD: /bin/rm -rf /datos/*
```

```bash
sudo chmod 440 /etc/sudoers.d/gatekeeper
```

## 7. Firewall

```bash
# Permitir NFS
sudo ufw allow from 192.168.10.0/24 to any port nfs

# Permitir SSH
sudo ufw allow ssh

# Habilitar firewall
sudo ufw enable
```

## 8. Copia la Llave SSH

Desde la Raspberry Pi:

```bash
ssh-copy-id gatekeeper@192.168.10.14
```

O manualmente, copia el contenido de `~/.ssh/id_rsa.pub` de la Pi
a `/home/gatekeeper/.ssh/authorized_keys` en el servidor.

## Verificacion

1. **Probar SSH sin contrasena:**
   ```bash
   ssh gatekeeper@192.168.10.14 "echo OK"
   ```

2. **Probar apagado:**
   ```bash
   ssh gatekeeper@192.168.10.14 "sudo poweroff"
   ```

3. **Probar WoL (desde la Pi):**
   ```bash
   wakeonlan b4:b5:2f:39:fd:d8
   ```

4. **Probar NFS:**
   ```bash
   sudo mount -t nfs 192.168.10.14:/datos /mnt/test
   ls /mnt/test
   sudo umount /mnt/test
   ```

## Troubleshooting

### El servidor no enciende con WoL

- Verifica que WoL esta habilitado en BIOS
- Verifica la direccion MAC: `ip link show enp0s3`
- Prueba con `wakeonlan -i 192.168.10.255 MAC`

### NFS no conecta

- Verifica firewall: `sudo ufw status`
- Verifica exports: `showmount -e 192.168.10.14`
- Verifica servicios: `systemctl status nfs-kernel-server`

### Cuotas no funcionan

- Verifica opciones en fstab: `usrquota,grpquota`
- Remonta: `sudo mount -o remount /datos`
- Reinicia cuotas: `sudo quotaoff /datos && sudo quotaon /datos`
