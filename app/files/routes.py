import os
import shutil
from pathlib import Path
from flask import render_template, jsonify, request, send_file, current_app, abort
from flask_login import login_required, current_user

from app.files import bp
from app.services.nfs import NFSService


def get_safe_path(relative_path: str) -> Path | None:
    """
    Validate and return safe absolute path within user's directory.
    Returns None if path is invalid or escapes user directory.
    """
    user_base = Path(NFSService.get_user_path(current_user.username))

    if not relative_path:
        return user_base

    # Normalize and resolve the path
    try:
        requested = (user_base / relative_path).resolve()
    except (ValueError, OSError):
        return None

    # Security check: ensure path is within user's directory
    try:
        requested.relative_to(user_base)
        return requested
    except ValueError:
        return None


def format_size(size_bytes: int) -> str:
    """Format bytes to human readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


@bp.route('/')
@login_required
def browser():
    """Render file browser view."""
    if not NFSService.is_mounted():
        return render_template('files/browser.html', mounted=False)
    return render_template('files/browser.html', mounted=True)


@bp.route('/api/list')
@login_required
def list_files():
    """List files in a directory."""
    if not NFSService.is_mounted():
        return jsonify({'error': 'Sistema de archivos no montado'}), 503

    relative_path = request.args.get('path', '')
    safe_path = get_safe_path(relative_path)

    if safe_path is None:
        return jsonify({'error': 'Ruta inválida'}), 400

    if not safe_path.exists():
        # Try to create user directory if it doesn't exist
        user_base = Path(NFSService.get_user_path(current_user.username))
        if safe_path == user_base:
            NFSService.ensure_user_directory(current_user.username)
        if not safe_path.exists():
            return jsonify({'error': 'Directorio no encontrado'}), 404

    if not safe_path.is_dir():
        return jsonify({'error': 'No es un directorio'}), 400

    items = []
    user_base = Path(NFSService.get_user_path(current_user.username))

    try:
        for entry in safe_path.iterdir():
            stat = entry.stat()
            rel_path = str(entry.relative_to(user_base))

            items.append({
                'name': entry.name,
                'path': rel_path,
                'is_dir': entry.is_dir(),
                'size': stat.st_size if not entry.is_dir() else None,
                'size_formatted': format_size(stat.st_size) if not entry.is_dir() else '-',
                'modified': stat.st_mtime,
                'modified_iso': os.path.getmtime(entry)
            })
    except PermissionError:
        return jsonify({'error': 'Permiso denegado'}), 403

    # Sort: directories first, then by name
    items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))

    # Calculate current path relative to user base
    current_rel = str(safe_path.relative_to(user_base)) if safe_path != user_base else ''

    return jsonify({
        'items': items,
        'current_path': current_rel,
        'parent_path': str(Path(current_rel).parent) if current_rel else None
    })


@bp.route('/api/download')
@login_required
def download():
    """Download a file."""
    if not NFSService.is_mounted():
        return jsonify({'error': 'Sistema de archivos no montado'}), 503

    relative_path = request.args.get('path', '')
    if not relative_path:
        return jsonify({'error': 'Ruta requerida'}), 400

    safe_path = get_safe_path(relative_path)

    if safe_path is None:
        return jsonify({'error': 'Ruta inválida'}), 400

    if not safe_path.exists():
        return jsonify({'error': 'Archivo no encontrado'}), 404

    if safe_path.is_dir():
        return jsonify({'error': 'No se puede descargar un directorio'}), 400

    return send_file(
        safe_path,
        as_attachment=True,
        download_name=safe_path.name
    )


@bp.route('/api/delete', methods=['DELETE'])
@login_required
def delete():
    """Delete a file or directory."""
    if not NFSService.is_mounted():
        return jsonify({'error': 'Sistema de archivos no montado'}), 503

    data = request.get_json()
    if not data or 'path' not in data:
        return jsonify({'error': 'Ruta requerida'}), 400

    safe_path = get_safe_path(data['path'])

    if safe_path is None:
        return jsonify({'error': 'Ruta inválida'}), 400

    # Prevent deleting root user directory
    user_base = Path(NFSService.get_user_path(current_user.username))
    if safe_path == user_base:
        return jsonify({'error': 'No se puede eliminar el directorio raíz'}), 400

    if not safe_path.exists():
        return jsonify({'error': 'Archivo no encontrado'}), 404

    try:
        if safe_path.is_dir():
            shutil.rmtree(safe_path)
        else:
            safe_path.unlink()
        return jsonify({'success': True, 'message': 'Eliminado correctamente'})
    except PermissionError:
        return jsonify({'error': 'Permiso denegado'}), 403
    except Exception as e:
        current_app.logger.error(f"Delete failed: {e}")
        return jsonify({'error': 'Error al eliminar'}), 500


@bp.route('/api/mkdir', methods=['POST'])
@login_required
def mkdir():
    """Create a new directory."""
    if not NFSService.is_mounted():
        return jsonify({'error': 'Sistema de archivos no montado'}), 503

    data = request.get_json()
    if not data or 'path' not in data or 'name' not in data:
        return jsonify({'error': 'Ruta y nombre requeridos'}), 400

    # Validate directory name
    name = data['name'].strip()
    if not name or '/' in name or '\\' in name or name in ('.', '..'):
        return jsonify({'error': 'Nombre de directorio inválido'}), 400

    parent_path = get_safe_path(data['path'])
    if parent_path is None:
        return jsonify({'error': 'Ruta inválida'}), 400

    new_dir = parent_path / name

    if new_dir.exists():
        return jsonify({'error': 'Ya existe un archivo o directorio con ese nombre'}), 409

    try:
        new_dir.mkdir(parents=False)
        return jsonify({'success': True, 'message': 'Directorio creado'})
    except PermissionError:
        return jsonify({'error': 'Permiso denegado'}), 403
    except Exception as e:
        current_app.logger.error(f"Mkdir failed: {e}")
        return jsonify({'error': 'Error al crear directorio'}), 500


@bp.route('/api/rename', methods=['POST'])
@login_required
def rename():
    """Rename a file or directory."""
    if not NFSService.is_mounted():
        return jsonify({'error': 'Sistema de archivos no montado'}), 503

    data = request.get_json()
    if not data or 'path' not in data or 'new_name' not in data:
        return jsonify({'error': 'Ruta y nuevo nombre requeridos'}), 400

    new_name = data['new_name'].strip()
    if not new_name or '/' in new_name or '\\' in new_name or new_name in ('.', '..'):
        return jsonify({'error': 'Nombre inválido'}), 400

    safe_path = get_safe_path(data['path'])
    if safe_path is None:
        return jsonify({'error': 'Ruta inválida'}), 400

    if not safe_path.exists():
        return jsonify({'error': 'Archivo no encontrado'}), 404

    new_path = safe_path.parent / new_name

    if new_path.exists():
        return jsonify({'error': 'Ya existe un archivo con ese nombre'}), 409

    try:
        safe_path.rename(new_path)
        return jsonify({'success': True, 'message': 'Renombrado correctamente'})
    except PermissionError:
        return jsonify({'error': 'Permiso denegado'}), 403
    except Exception as e:
        current_app.logger.error(f"Rename failed: {e}")
        return jsonify({'error': 'Error al renombrar'}), 500
