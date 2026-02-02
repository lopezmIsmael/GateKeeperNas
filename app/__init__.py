import os
from flask import Flask
from flask_login import LoginManager

from app.config import config

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
login_manager.login_message_category = 'warning'


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])

    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    # Ensure upload temp dir exists
    os.makedirs(app.config['UPLOAD_TEMP_DIR'], exist_ok=True)

    # Initialize extensions
    login_manager.init_app(app)

    # Initialize database
    from app.models import db, init_db
    db.init_app(app)

    with app.app_context():
        init_db()

    # Register blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from app.dashboard import bp as dashboard_bp
    app.register_blueprint(dashboard_bp)

    from app.files import bp as files_bp
    app.register_blueprint(files_bp)

    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp)

    # User loader for Flask-Login
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    return app
