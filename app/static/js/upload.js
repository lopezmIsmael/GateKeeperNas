// Chunked Upload JavaScript

(function() {
    'use strict';

    // Configuration
    const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB chunks

    // State
    let currentUpload = null;

    // DOM Elements
    const fileInput = document.getElementById('file-input');
    const btnUpload = document.getElementById('btn-upload');
    const uploadProgress = document.getElementById('upload-progress');
    const uploadFilename = document.getElementById('upload-filename');
    const uploadBar = document.getElementById('upload-bar');
    const btnCancelUpload = document.getElementById('btn-cancel-upload');

    // Utility Functions
    function showToast(message, type = 'info') {
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(container);
        }

        const toastHtml = `
            <div class="toast align-items-center text-white bg-${type} border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;

        container.insertAdjacentHTML('beforeend', toastHtml);
        const toast = container.lastElementChild;
        new bootstrap.Toast(toast).show();
        toast.addEventListener('hidden.bs.toast', () => toast.remove());
    }

    function updateProgress(percent, filename) {
        uploadFilename.textContent = `Subiendo: ${filename}`;
        uploadBar.style.width = percent + '%';
        uploadBar.textContent = Math.round(percent) + '%';
    }

    // Upload Functions
    async function initUpload(file) {
        const totalChunks = Math.ceil(file.size / CHUNK_SIZE);

        try {
            const response = await fetch('/files/api/upload/init', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    filename: file.name,
                    destination: window.FileBrowser.getCurrentPath(),
                    total_size: file.size,
                    total_chunks: totalChunks
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Error al iniciar subida');
            }

            return data.session_id;
        } catch (error) {
            throw error;
        }
    }

    async function uploadChunk(sessionId, file, chunkNumber) {
        const start = chunkNumber * CHUNK_SIZE;
        const end = Math.min(start + CHUNK_SIZE, file.size);
        const chunk = file.slice(start, end);

        const formData = new FormData();
        formData.append('session_id', sessionId);
        formData.append('chunk_number', chunkNumber);
        formData.append('chunk', chunk);

        const response = await fetch('/files/api/upload/chunk', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Error al subir chunk');
        }

        return data;
    }

    async function completeUpload(sessionId) {
        const response = await fetch('/files/api/upload/complete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Error al completar subida');
        }

        return data;
    }

    async function cancelUpload(sessionId) {
        try {
            await fetch('/files/api/upload/cancel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: sessionId })
            });
        } catch (error) {
            console.error('Error canceling upload:', error);
        }
    }

    async function uploadFile(file) {
        const totalChunks = Math.ceil(file.size / CHUNK_SIZE);

        // Show progress UI
        uploadProgress.classList.remove('d-none');
        updateProgress(0, file.name);

        try {
            // Initialize upload session
            const sessionId = await initUpload(file);
            currentUpload = { sessionId, cancelled: false };

            // Upload chunks
            for (let i = 0; i < totalChunks; i++) {
                if (currentUpload.cancelled) {
                    await cancelUpload(sessionId);
                    throw new Error('Subida cancelada');
                }

                await uploadChunk(sessionId, file, i);
                const progress = ((i + 1) / totalChunks) * 100;
                updateProgress(progress, file.name);
            }

            // Complete upload
            await completeUpload(sessionId);
            showToast(`${file.name} subido correctamente`, 'success');

            // Refresh file list
            window.FileBrowser.refresh();

        } catch (error) {
            if (error.message !== 'Subida cancelada') {
                showToast(error.message, 'danger');
            }
        } finally {
            uploadProgress.classList.add('d-none');
            currentUpload = null;
            fileInput.value = '';
        }
    }

    async function uploadMultipleFiles(files) {
        for (const file of files) {
            if (currentUpload && currentUpload.cancelled) break;
            await uploadFile(file);
        }
    }

    // Event Listeners
    btnUpload.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            uploadMultipleFiles(Array.from(fileInput.files));
        }
    });

    btnCancelUpload.addEventListener('click', () => {
        if (currentUpload) {
            currentUpload.cancelled = true;
            showToast('Cancelando subida...', 'warning');
        }
    });

    // Drag and drop support
    const dropZone = document.querySelector('.card');
    if (dropZone) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(event => {
            dropZone.addEventListener(event, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });

        ['dragenter', 'dragover'].forEach(event => {
            dropZone.addEventListener(event, () => {
                dropZone.classList.add('border', 'border-primary');
            });
        });

        ['dragleave', 'drop'].forEach(event => {
            dropZone.addEventListener(event, () => {
                dropZone.classList.remove('border', 'border-primary');
            });
        });

        dropZone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                uploadMultipleFiles(Array.from(files));
            }
        });
    }
})();
