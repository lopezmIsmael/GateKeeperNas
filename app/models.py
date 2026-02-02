from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    quota_gb = db.Column(db.Integer, default=500, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    logs = db.relationship('ServerLog', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class ServerLog(db.Model):
    __tablename__ = 'server_logs'

    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(32), nullable=False)  # 'wake', 'shutdown', 'mount', 'unmount'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    details = db.Column(db.String(256))
    success = db.Column(db.Boolean, default=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f'<ServerLog {self.action} at {self.timestamp}>'


class UploadSession(db.Model):
    __tablename__ = 'upload_sessions'

    id = db.Column(db.String(36), primary_key=True)  # UUID
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(256), nullable=False)
    destination_path = db.Column(db.String(512), nullable=False)
    total_size = db.Column(db.BigInteger, nullable=False)
    total_chunks = db.Column(db.Integer, nullable=False)
    chunks_received = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref='upload_sessions')

    def __repr__(self):
        return f'<UploadSession {self.filename} ({self.chunks_received}/{self.total_chunks})>'


def init_db():
    from sqlalchemy import inspect
    inspector = inspect(db.engine)

    # Only create tables if they don't exist
    if not inspector.has_table('users'):
        db.create_all()

    # Create default admin user if not exists
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            is_admin=True,
            quota_gb=0  # Admin has no quota limit
        )
        admin.set_password('admin')  # Change this in production!
        db.session.add(admin)
        db.session.commit()
