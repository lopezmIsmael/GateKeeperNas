# Gatekeeper NAS - Dockerfile
# Compatible con Raspberry Pi (ARM64) y x86_64

FROM python:3.11-slim

# Metadata
LABEL maintainer="Gatekeeper NAS"
LABEL description="NAS Control Panel for Raspberry Pi"

# Evitar prompts interactivos
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Para NFS mount
    nfs-common \
    # Para Wake-on-LAN
    wakeonlan \
    iputils-ping \
    # Para SSH
    openssh-client \
    # Utilidades
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root para la aplicacion
RUN useradd -m -s /bin/bash gatekeeper && \
    mkdir -p /app /mnt/servidor /data && \
    chown -R gatekeeper:gatekeeper /app /data

# Configurar sudo para mount/umount sin password
RUN echo "gatekeeper ALL=(ALL) NOPASSWD: /bin/mount, /bin/umount, /sbin/mount.nfs" >> /etc/sudoers.d/gatekeeper && \
    chmod 440 /etc/sudoers.d/gatekeeper

# Directorio de trabajo
WORKDIR /app

# Copiar requirements primero (para cache de Docker)
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copiar el resto de la aplicacion
COPY --chown=gatekeeper:gatekeeper . .

# Crear directorios necesarios
RUN mkdir -p /app/instance /tmp/gatekeeper_uploads && \
    chown -R gatekeeper:gatekeeper /app/instance /tmp/gatekeeper_uploads

# Puerto de la aplicacion
EXPOSE 5000

# Cambiar a usuario no-root
USER gatekeeper

# Variables de entorno por defecto
ENV FLASK_ENV=production
ENV NFS_MOUNT_POINT=/mnt/servidor
ENV UPLOAD_TEMP_DIR=/tmp/gatekeeper_uploads

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/auth/login')" || exit 1

# Comando de inicio
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "app:create_app()"]
