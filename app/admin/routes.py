from functools import wraps
from flask import render_template, jsonify, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user

from app.admin import bp
from app.models import db, User, ServerLog
from app.services.quota import QuotaService
from app.services.power import PowerService


def admin_required(f):
    """Decorator to require admin privileges."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            if request.is_json:
                return jsonify({'error': 'Acceso denegado'}), 403
            flash('No tienes permisos para acceder a esta sección', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/')
@login_required
@admin_required
def index():
    """Admin dashboard."""
    users = User.query.all()
    recent_logs = ServerLog.query.order_by(ServerLog.timestamp.desc()).limit(20).all()
    return render_template('admin/users.html', users=users, logs=recent_logs)


@bp.route('/users')
@login_required
@admin_required
def list_users():
    """List all users."""
    users = User.query.all()
    return render_template('admin/users.html', users=users)


@bp.route('/users/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    """Create a new user."""
    if request.method == 'GET':
        return render_template('admin/user_form.html', user=None)

    # POST - create user
    username = request.form.get('username', '').strip().lower()
    password = request.form.get('password', '')
    quota_gb = request.form.get('quota_gb', type=int) or current_app.config['DEFAULT_QUOTA_GB']
    is_admin = request.form.get('is_admin') == 'on'

    # Validation
    if not username or len(username) < 3:
        flash('El nombre de usuario debe tener al menos 3 caracteres', 'danger')
        return render_template('admin/user_form.html', user=None)

    if not username.isalnum():
        flash('El nombre de usuario solo puede contener letras y números', 'danger')
        return render_template('admin/user_form.html', user=None)

    if not password or len(password) < 6:
        flash('La contraseña debe tener al menos 6 caracteres', 'danger')
        return render_template('admin/user_form.html', user=None)

    if User.query.filter_by(username=username).first():
        flash('Ya existe un usuario con ese nombre', 'danger')
        return render_template('admin/user_form.html', user=None)

    # Create user in database
    user = User(username=username, is_admin=is_admin, quota_gb=quota_gb)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    # Setup on server if online
    if PowerService.ping():
        if not QuotaService.setup_new_user(username, quota_gb):
            flash('Usuario creado localmente, pero hubo un error al configurar en el servidor', 'warning')
        else:
            flash(f'Usuario {username} creado correctamente', 'success')
    else:
        flash(f'Usuario {username} creado. Configura el servidor cuando esté online.', 'warning')

    return redirect(url_for('admin.list_users'))


@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit a user."""
    user = User.query.get_or_404(user_id)

    if request.method == 'GET':
        return render_template('admin/user_form.html', user=user)

    # POST - update user
    new_password = request.form.get('password', '')
    quota_gb = request.form.get('quota_gb', type=int) or user.quota_gb
    is_admin = request.form.get('is_admin') == 'on'

    # Don't allow removing admin from self
    if user.id == current_user.id and not is_admin:
        flash('No puedes quitarte los permisos de administrador', 'danger')
        return render_template('admin/user_form.html', user=user)

    user.is_admin = is_admin

    # Update password if provided
    if new_password:
        if len(new_password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres', 'danger')
            return render_template('admin/user_form.html', user=user)
        user.set_password(new_password)

    # Update quota if changed
    if quota_gb != user.quota_gb:
        user.quota_gb = quota_gb
        if PowerService.ping():
            if not QuotaService.set_quota(user.username, quota_gb):
                flash('Error al actualizar cuota en el servidor', 'warning')

    db.session.commit()
    flash(f'Usuario {user.username} actualizado', 'success')
    return redirect(url_for('admin.list_users'))


@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user."""
    user = User.query.get_or_404(user_id)

    # Don't allow deleting self
    if user.id == current_user.id:
        flash('No puedes eliminar tu propia cuenta', 'danger')
        return redirect(url_for('admin.list_users'))

    # Don't allow deleting other admins
    if user.is_admin:
        flash('No puedes eliminar a otro administrador', 'danger')
        return redirect(url_for('admin.list_users'))

    username = user.username

    # Remove from server if online
    if PowerService.ping():
        QuotaService.remove_user(username)

    # Delete from database
    db.session.delete(user)
    db.session.commit()

    flash(f'Usuario {username} eliminado', 'success')
    return redirect(url_for('admin.list_users'))


@bp.route('/users/<int:user_id>/sync', methods=['POST'])
@login_required
@admin_required
def sync_user(user_id):
    """Sync user configuration to server."""
    user = User.query.get_or_404(user_id)

    if not PowerService.ping():
        return jsonify({'error': 'Servidor no disponible'}), 503

    if QuotaService.setup_new_user(user.username, user.quota_gb):
        return jsonify({'success': True, 'message': f'Usuario {user.username} sincronizado'})
    else:
        return jsonify({'error': 'Error al sincronizar usuario'}), 500


@bp.route('/api/users')
@login_required
@admin_required
def api_list_users():
    """API: List all users with quota info."""
    users = User.query.all()
    server_online = PowerService.ping()

    result = []
    for user in users:
        user_data = {
            'id': user.id,
            'username': user.username,
            'is_admin': user.is_admin,
            'quota_gb': user.quota_gb,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'quota_used': None
        }

        # Get actual quota usage if server is online
        if server_online and not user.is_admin:
            quota_info = QuotaService.get_quota(user.username)
            if quota_info:
                user_data['quota_used'] = quota_info.get('used_gb', 0)

        result.append(user_data)

    return jsonify(result)


@bp.route('/logs')
@login_required
@admin_required
def view_logs():
    """View server action logs."""
    page = request.args.get('page', 1, type=int)
    logs = ServerLog.query.order_by(ServerLog.timestamp.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    return render_template('admin/logs.html', logs=logs)
