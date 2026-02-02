import os
import uuid
from pathlib import Path
from flask import request, jsonify, current_app
from flask_login import login_required, current_user

from app.files import bp
from app.files.routes import get_safe_path
from app.models import db, UploadSession
from app.services.nfs import NFSService


def get_temp_dir(session_id: str) -> Path:
    """Get temporary directory for upload chunks."""
    temp_base = Path(current_app.config['UPLOAD_TEMP_DIR'])
    return temp_base / session_id


@bp.route('/api/upload/init', methods=['POST'])
@login_required
def upload_init():
    """Initialize a chunked upload session."""
    if not NFSService.is_mounted():
        return jsonify({'error': 'Sistema de archivos no montado'}), 503

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Datos requeridos'}), 400

    filename = data.get('filename', '').strip()
    destination = data.get('destination', '')
    total_size = data.get('total_size', 0)
    total_chunks = data.get('total_chunks', 0)

    if not filename or total_size <= 0 or total_chunks <= 0:
        return jsonify({'error': 'Parámetros inválidos'}), 400

    # Validate filename
    if '/' in filename or '\\' in filename or filename in ('.', '..'):
        return jsonify({'error': 'Nombre de archivo inválido'}), 400

    # Validate destination path
    dest_path = get_safe_path(destination)
    if dest_path is None:
        return jsonify({'error': 'Destino inválido'}), 400

    if not dest_path.is_dir():
        return jsonify({'error': 'El destino no es un directorio'}), 400

    # Check if file already exists
    final_path = dest_path / filename
    if final_path.exists():
        return jsonify({'error': 'Ya existe un archivo con ese nombre'}), 409

    # Create upload session
    session_id = str(uuid.uuid4())
    session = UploadSession(
        id=session_id,
        user_id=current_user.id,
        filename=filename,
        destination_path=str(dest_path),
        total_size=total_size,
        total_chunks=total_chunks
    )

    db.session.add(session)
    db.session.commit()

    # Create temp directory for chunks
    temp_dir = get_temp_dir(session_id)
    temp_dir.mkdir(parents=True, exist_ok=True)

    return jsonify({
        'success': True,
        'session_id': session_id,
        'message': 'Sesión de subida iniciada'
    })


@bp.route('/api/upload/chunk', methods=['POST'])
@login_required
def upload_chunk():
    """Receive a file chunk."""
    session_id = request.form.get('session_id')
    chunk_number = request.form.get('chunk_number', type=int)
    chunk_file = request.files.get('chunk')

    if not session_id or chunk_number is None or not chunk_file:
        return jsonify({'error': 'Parámetros incompletos'}), 400

    # Get upload session
    session = UploadSession.query.filter_by(
        id=session_id,
        user_id=current_user.id,
        completed=False
    ).first()

    if not session:
        return jsonify({'error': 'Sesión de subida no encontrada'}), 404

    if chunk_number < 0 or chunk_number >= session.total_chunks:
        return jsonify({'error': 'Número de chunk inválido'}), 400

    # Save chunk to temp directory
    temp_dir = get_temp_dir(session_id)
    chunk_path = temp_dir / f"chunk_{chunk_number:06d}"

    try:
        chunk_file.save(str(chunk_path))
        session.chunks_received += 1
        db.session.commit()

        return jsonify({
            'success': True,
            'chunks_received': session.chunks_received,
            'total_chunks': session.total_chunks
        })
    except Exception as e:
        current_app.logger.error(f"Chunk upload failed: {e}")
        return jsonify({'error': 'Error al guardar chunk'}), 500


@bp.route('/api/upload/complete', methods=['POST'])
@login_required
def upload_complete():
    """Finalize upload by assembling chunks."""
    data = request.get_json()
    session_id = data.get('session_id') if data else None

    if not session_id:
        return jsonify({'error': 'session_id requerido'}), 400

    session = UploadSession.query.filter_by(
        id=session_id,
        user_id=current_user.id,
        completed=False
    ).first()

    if not session:
        return jsonify({'error': 'Sesión no encontrada'}), 404

    if session.chunks_received != session.total_chunks:
        return jsonify({
            'error': f'Faltan chunks ({session.chunks_received}/{session.total_chunks})'
        }), 400

    temp_dir = get_temp_dir(session_id)
    final_path = Path(session.destination_path) / session.filename

    try:
        # Assemble chunks
        with open(final_path, 'wb') as output:
            for i in range(session.total_chunks):
                chunk_path = temp_dir / f"chunk_{i:06d}"
                if not chunk_path.exists():
                    raise FileNotFoundError(f"Chunk {i} not found")

                with open(chunk_path, 'rb') as chunk:
                    output.write(chunk.read())

        # Verify file size
        if final_path.stat().st_size != session.total_size:
            final_path.unlink()
            raise ValueError("File size mismatch")

        # Mark session as completed
        session.completed = True
        db.session.commit()

        # Clean up temp directory
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

        return jsonify({
            'success': True,
            'message': 'Archivo subido correctamente',
            'filename': session.filename
        })

    except Exception as e:
        current_app.logger.error(f"Upload assembly failed: {e}")
        # Clean up on failure
        if final_path.exists():
            final_path.unlink()
        return jsonify({'error': 'Error al ensamblar archivo'}), 500


@bp.route('/api/upload/cancel', methods=['POST'])
@login_required
def upload_cancel():
    """Cancel an upload session."""
    data = request.get_json()
    session_id = data.get('session_id') if data else None

    if not session_id:
        return jsonify({'error': 'session_id requerido'}), 400

    session = UploadSession.query.filter_by(
        id=session_id,
        user_id=current_user.id,
        completed=False
    ).first()

    if not session:
        return jsonify({'error': 'Sesión no encontrada'}), 404

    # Clean up temp directory
    temp_dir = get_temp_dir(session_id)
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)

    # Delete session
    db.session.delete(session)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Subida cancelada'
    })


@bp.route('/api/upload/status/<session_id>')
@login_required
def upload_status(session_id):
    """Get upload session status."""
    session = UploadSession.query.filter_by(
        id=session_id,
        user_id=current_user.id
    ).first()

    if not session:
        return jsonify({'error': 'Sesión no encontrada'}), 404

    return jsonify({
        'session_id': session.id,
        'filename': session.filename,
        'total_size': session.total_size,
        'total_chunks': session.total_chunks,
        'chunks_received': session.chunks_received,
        'completed': session.completed,
        'progress': (session.chunks_received / session.total_chunks) * 100 if session.total_chunks > 0 else 0
    })
