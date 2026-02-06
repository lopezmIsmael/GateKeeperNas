import os
import shutil
import mimetypes
from datetime import datetime
from pathlib import Path
from flask import render_template, jsonify, request, send_file, current_app, abort, Response
from flask_login import login_required, current_user
from werkzeug.utils import safe_join

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
            
            # Get MIME type for files
            mime_type = None
            if not entry.is_dir():
                mime_type, _ = mimetypes.guess_type(entry.name)
            
            items.append({
                'name': entry.name,
                'path': rel_path,
                'is_dir': entry.is_dir(),
                'size': stat.st_size if not entry.is_dir() else None,
                'size_formatted': format_size(stat.st_size) if not entry.is_dir() else '-',
                'modified': stat.st_mtime,
                'modified_iso': os.path.getmtime(entry),
                'created': stat.st_ctime,
                'mime_type': mime_type
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


@bp.route('/api/file-info')
@login_required
def file_info():
    """Get detailed file information and metadata."""
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
        return jsonify({'error': 'Es un directorio'}), 400

    try:
        stat = safe_path.stat()
        mime_type, encoding = mimetypes.guess_type(safe_path.name)
        
        file_info = {
            'name': safe_path.name,
            'path': relative_path,
            'size': stat.st_size,
            'size_formatted': format_size(stat.st_size),
            'modified': stat.st_mtime,
            'modified_formatted': datetime.fromtimestamp(stat.st_mtime).strftime('%d/%m/%Y %H:%M:%S'),
            'created': stat.st_ctime,
            'created_formatted': datetime.fromtimestamp(stat.st_ctime).strftime('%d/%m/%Y %H:%M:%S'),
            'mime_type': mime_type or 'application/octet-stream',
            'encoding': encoding,
            'extension': safe_path.suffix.lower(),
            'is_text': is_text_file(mime_type),
            'is_image': is_image_file(mime_type),
            'is_video': is_video_file(mime_type),
            'is_audio': is_audio_file(mime_type),
            'is_pdf': mime_type == 'application/pdf',
            'is_office': is_office_file(safe_path.suffix.lower()),
            'can_preview': can_preview_file(mime_type, safe_path.suffix.lower())
        }
        
        return jsonify(file_info)
    except Exception as e:
        current_app.logger.error(f"File info failed: {e}")
        return jsonify({'error': 'Error al obtener información del archivo'}), 500


@bp.route('/api/preview')
@login_required
def preview():
    """Preview file content for supported file types."""
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
        return jsonify({'error': 'Es un directorio'}), 400

    try:
        mime_type, _ = mimetypes.guess_type(safe_path.name)
        
        # For images, videos, audio, and PDFs, serve the file directly
        if is_image_file(mime_type) or is_video_file(mime_type) or \
           is_audio_file(mime_type) or mime_type == 'application/pdf':
            return send_file(safe_path, mimetype=mime_type)
        
        # For text files, read content
        if is_text_file(mime_type) or safe_path.suffix.lower() in ['.md', '.txt', '.json', '.xml', '.csv']:
            try:
                with open(safe_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return jsonify({
                    'content': content,
                    'mime_type': mime_type or 'text/plain'
                })
            except UnicodeDecodeError:
                return jsonify({'error': 'No se puede previsualizar este archivo de texto'}), 400
        
        return jsonify({'error': 'Tipo de archivo no soportado para previsualización'}), 400
        
    except Exception as e:
        current_app.logger.error(f"Preview failed: {e}")
        return jsonify({'error': 'Error al previsualizar archivo'}), 500


@bp.route('/api/serve/<path:filepath>')
@login_required
def serve_file(filepath):
    """Serve file for inline viewing (not download)."""
    if not NFSService.is_mounted():
        abort(503)

    safe_path = get_safe_path(filepath)

    if safe_path is None or not safe_path.exists() or safe_path.is_dir():
        abort(404)

    mime_type, _ = mimetypes.guess_type(safe_path.name)
    return send_file(safe_path, mimetype=mime_type, as_attachment=False)


def is_text_file(mime_type: str | None) -> bool:
    """Check if file is a text file."""
    if not mime_type:
        return False
    return mime_type.startswith('text/')


def is_image_file(mime_type: str | None) -> bool:
    """Check if file is an image."""
    if not mime_type:
        return False
    return mime_type.startswith('image/')


def is_video_file(mime_type: str | None) -> bool:
    """Check if file is a video."""
    if not mime_type:
        return False
    return mime_type.startswith('video/')


def is_audio_file(mime_type: str | None) -> bool:
    """Check if file is audio."""
    if not mime_type:
        return False
    return mime_type.startswith('audio/')


def is_office_file(extension: str) -> bool:
    """Check if file is a Microsoft Office document."""
    office_extensions = ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
    return extension in office_extensions


def can_preview_file(mime_type: str | None, extension: str) -> bool:
    """Check if file can be previewed."""
    if not mime_type:
        return False
    
    # Check by MIME type
    if mime_type.startswith(('image/', 'video/', 'audio/', 'text/')):
        return True
    
    if mime_type == 'application/pdf':
        return True
    
    # Check by extension
    previewable_extensions = ['.md', '.txt', '.json', '.xml', '.csv', '.log', 
                             '.py', '.js', '.html', '.css', '.yaml', '.yml']
    if extension in previewable_extensions:
        return True
    
    # Office files (will use viewer)
    if is_office_file(extension):
        return True
    
    return False
