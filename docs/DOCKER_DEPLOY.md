# Despliegue con Docker en Raspberry Pi

Esta guia explica como desplegar Gatekeeper NAS usando Docker en una Raspberry Pi.

## Requisitos Previos

### En la Raspberry Pi

1. **Raspberry Pi OS (64-bit)** - Recomendado Bookworm o superior
2. **Docker instalado**:
   ```bash
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER
   # Cerrar sesion y volver a entrar
   ```

3. **Docker Compose**:
   ```bash
   sudo apt install docker-compose-plugin
   ```

4. **Crear punto de montaje NFS**:
   ```bash
   sudo mkdir -p /mnt/servidor
   sudo chown $USER:$USER /mnt/servidor
   ```

5. **Generar llave SSH** (si no existe):
   ```bash
   ssh-keygen -t rsa -b 4096
   # Copiar al servidor
   ssh-copy-id gatekeeper@192.168.10.14
   ```

## Despliegue

### 1. Clonar o copiar el proyecto

```bash
# Opcion A: Clonar desde git
git clone https://tu-repo/GatekeeperNAS.git
cd GatekeeperNAS

# Opcion B: Copiar con scp
scp -r GatekeeperNAS/ pi@raspberry:/home/pi/
```

### 2. Configurar variables de entorno

```bash
cp .env.docker .env
nano .env
```

Ajusta los valores segun tu configuracion:
- `SECRET_KEY`: Genera una clave segura con `openssl rand -hex 32`
- `SERVER_IP`: IP de tu servidor Ubuntu
- `SERVER_MAC`: MAC del servidor (para WoL)
- `SSH_KEY_PATH`: Ruta a tu llave SSH

### 3. Construir y ejecutar

```bash
# Construir la imagen
docker compose build

# Iniciar en segundo plano
docker compose up -d

# Ver logs
docker compose logs -f
```

### 4. Verificar

Accede a `http://<IP-RASPBERRY>:5000`

Usuario por defecto: `admin` / `admin`

**IMPORTANTE**: Cambia la contrasena del admin inmediatamente.

## Comandos Utiles

```bash
# Ver estado
docker compose ps

# Ver logs en tiempo real
docker compose logs -f gatekeeper

# Reiniciar
docker compose restart

# Detener
docker compose down

# Actualizar (despues de cambios)
docker compose build --no-cache
docker compose up -d
```

## Estructura de Volumenes

| Volumen | Proposito |
|---------|-----------|
| `gatekeeper_data` | Base de datos SQLite |
| `gatekeeper_uploads` | Archivos temporales de subida |
| `/mnt/servidor` | Punto de montaje NFS (bind mount) |

## Persistencia de Datos

Los datos importantes se guardan en volumenes Docker:

```bash
# Ver volumenes
docker volume ls

# Backup de la base de datos
docker cp gatekeeper-nas:/app/instance/gatekeeper.db ./backup/
```

## Troubleshooting

### El contenedor no puede montar NFS

1. Verifica que el servidor este encendido
2. Verifica permisos en `/mnt/servidor`:
   ```bash
   sudo chmod 755 /mnt/servidor
   ```
3. Prueba montar manualmente:
   ```bash
   sudo mount -t nfs 192.168.10.14:/datos /mnt/servidor
   ```

### Wake-on-LAN no funciona

El contenedor usa `network_mode: host` para enviar paquetes broadcast.
Verifica que WoL este habilitado en el servidor (BIOS + Linux).

### SSH falla

1. Verifica que la llave SSH este correctamente montada:
   ```bash
   docker exec gatekeeper-nas ls -la /home/gatekeeper/.ssh/
   ```
2. Verifica permisos de la llave en el host:
   ```bash
   chmod 600 ~/.ssh/id_rsa
   ```

### Ver logs detallados

```bash
docker compose logs --tail=100 gatekeeper
```

## Actualizacion

```bash
cd GatekeeperNAS
git pull  # o reemplaza los archivos manualmente
docker compose build --no-cache
docker compose up -d
```

## Seguridad en Produccion

1. **Cambiar SECRET_KEY**: Genera una clave unica
2. **Cambiar password admin**: Hazlo desde la interfaz web
3. **HTTPS**: Usa un reverse proxy (nginx/traefik) con certificado SSL
4. **Firewall**: Limita acceso al puerto 5000

### Ejemplo con Nginx (reverse proxy)

```nginx
server {
    listen 80;
    server_name nas.tudominio.local;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # Para uploads grandes
        client_max_body_size 100M;
    }
}
```
