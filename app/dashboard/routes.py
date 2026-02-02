from flask import render_template, jsonify, current_app
from flask_login import login_required, current_user

from app.dashboard import bp
from app.models import db, ServerLog
from app.services.power import PowerService
from app.services.nfs import NFSService


@bp.route('/')
@bp.route('/dashboard')
@login_required
def index():
    return render_template('dashboard/index.html')


@bp.route('/api/server/status')
@login_required
def server_status():
    """Get current server status."""
    status = PowerService.get_status()
    status['nfs_mounted'] = NFSService.is_mounted()
    return jsonify(status)


@bp.route('/api/server/wake', methods=['POST'])
@login_required
def wake_server():
    """Send Wake-on-LAN packet to server."""
    success = PowerService.send_wol()

    # Log the action
    log = ServerLog(
        action='wake',
        user_id=current_user.id,
        success=success,
        details=f"WoL sent to {current_app.config['SERVER_MAC']}"
    )
    db.session.add(log)
    db.session.commit()

    if success:
        return jsonify({
            'success': True,
            'message': 'Paquete Wake-on-LAN enviado. El servidor tardará unos segundos en encender.'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Error al enviar paquete Wake-on-LAN'
        }), 500


@bp.route('/api/server/shutdown', methods=['POST'])
@login_required
def shutdown_server():
    """Shutdown the server via SSH."""
    if not current_user.is_admin:
        return jsonify({
            'success': False,
            'message': 'Solo los administradores pueden apagar el servidor'
        }), 403

    # First unmount NFS
    NFSService.unmount()

    success = PowerService.shutdown()

    # Log the action
    log = ServerLog(
        action='shutdown',
        user_id=current_user.id,
        success=success
    )
    db.session.add(log)
    db.session.commit()

    if success:
        return jsonify({
            'success': True,
            'message': 'Comando de apagado enviado al servidor'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Error al enviar comando de apagado'
        }), 500


@bp.route('/api/server/mount', methods=['POST'])
@login_required
def mount_nfs():
    """Mount NFS share."""
    if not PowerService.ping():
        return jsonify({
            'success': False,
            'message': 'El servidor no está disponible'
        }), 503

    success = NFSService.mount()

    log = ServerLog(
        action='mount',
        user_id=current_user.id,
        success=success
    )
    db.session.add(log)
    db.session.commit()

    if success:
        return jsonify({
            'success': True,
            'message': 'Sistema de archivos montado correctamente'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Error al montar sistema de archivos'
        }), 500


@bp.route('/api/server/unmount', methods=['POST'])
@login_required
def unmount_nfs():
    """Unmount NFS share."""
    success = NFSService.unmount()

    log = ServerLog(
        action='unmount',
        user_id=current_user.id,
        success=success
    )
    db.session.add(log)
    db.session.commit()

    if success:
        return jsonify({
            'success': True,
            'message': 'Sistema de archivos desmontado'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Error al desmontar sistema de archivos'
        }), 500
