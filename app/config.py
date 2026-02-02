import os
from pathlib import Path

basedir = Path(__file__).parent.parent


class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production'

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f"sqlite:///{basedir / 'instance' / 'gatekeeper.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Server Configuration
    SERVER_IP = os.environ.get('SERVER_IP') or '192.168.10.14'
    SERVER_MAC = os.environ.get('SERVER_MAC') or 'b4:b5:2f:39:fd:d8'
    SERVER_BROADCAST = os.environ.get('SERVER_BROADCAST') or '192.168.10.255'

    # NFS Configuration
    NFS_MOUNT_POINT = os.environ.get('NFS_MOUNT_POINT') or '/mnt/servidor'
    NFS_EXPORT = os.environ.get('NFS_EXPORT') or '192.168.10.14:/datos'

    # SSH Configuration
    SSH_USER = os.environ.get('SSH_USER') or 'gatekeeper'
    SSH_KEY_PATH = os.environ.get('SSH_KEY_PATH') or os.path.expanduser('~/.ssh/id_rsa')
    SSH_PORT = int(os.environ.get('SSH_PORT') or 22)

    # Quota Configuration
    DEFAULT_QUOTA_GB = int(os.environ.get('DEFAULT_QUOTA_GB') or 500)
    QUOTA_MOUNT_POINT = os.environ.get('QUOTA_MOUNT_POINT') or '/datos'

    # Upload Configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max per request (chunks)
    CHUNK_SIZE = 5 * 1024 * 1024  # 5MB chunks
    UPLOAD_TEMP_DIR = os.environ.get('UPLOAD_TEMP_DIR') or '/tmp/gatekeeper_uploads'

    # Timeouts
    PING_TIMEOUT = 2  # seconds
    WOL_WAIT_TIME = 60  # seconds to wait after WoL
    SSH_TIMEOUT = 10  # seconds


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
