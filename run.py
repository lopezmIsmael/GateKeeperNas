#!/usr/bin/env python3
"""
Gatekeeper NAS - Entry Point

Run with: python run.py
Or in production: gunicorn -w 4 -b 0.0.0.0:5000 'app:create_app()'
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app import create_app

app = create_app()

if __name__ == '__main__':
    # Development server
    debug = os.environ.get('FLASK_DEBUG', '1') == '1'
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))

    print(f"""
    ╔═══════════════════════════════════════════════════════════╗
    ║                    GATEKEEPER NAS                         ║
    ║              Control Centralizado de Almacenamiento       ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  Servidor: http://{host}:{port}                          ║
    ║  Modo: {'Desarrollo' if debug else 'Produccion'}                                     ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    app.run(host=host, port=port, debug=debug)
