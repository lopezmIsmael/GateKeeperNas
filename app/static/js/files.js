// File Browser JavaScript

(function() {
    'use strict';

    // State
    let currentPath = '';

    // DOM Elements
    const fileList = document.getElementById('file-list');
    const breadcrumb = document.getElementById('breadcrumb');
    const newFolderModal = new bootstrap.Modal(document.getElementById('newFolderModal'));
    const renameModal = new bootstrap.Modal(document.getElementById('renameModal'));
    const deleteModal = new bootstrap.Modal(document.getElementById('deleteModal'));

    // Utility Functions
    function formatDate(timestamp) {
        const date = new Date(timestamp * 1000);
        return date.toLocaleDateString('es-ES', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    function getFileIcon(filename, isDir) {
        if (isDir) return '<i class="bi bi-folder-fill folder-icon"></i>';

        const ext = filename.split('.').pop().toLowerCase();
        const iconMap = {
            // Images
            'jpg': 'bi-file-image text-success',
            'jpeg': 'bi-file-image text-success',
            'png': 'bi-file-image text-success',
            'gif': 'bi-file-image text-success',
            'svg': 'bi-file-image text-success',
            'webp': 'bi-file-image text-success',
            // Documents
            'pdf': 'bi-file-pdf text-danger',
            'doc': 'bi-file-word text-primary',
            'docx': 'bi-file-word text-primary',
            'xls': 'bi-file-excel text-success',
            'xlsx': 'bi-file-excel text-success',
            'ppt': 'bi-file-ppt text-warning',
            'pptx': 'bi-file-ppt text-warning',
            'txt': 'bi-file-text',
            // Code
            'js': 'bi-file-code text-warning',
            'py': 'bi-file-code text-info',
            'html': 'bi-file-code text-danger',
            'css': 'bi-file-code text-primary',
            'json': 'bi-file-code text-warning',
            // Archives
            'zip': 'bi-file-zip text-warning',
            'rar': 'bi-file-zip text-warning',
            'tar': 'bi-file-zip text-warning',
            'gz': 'bi-file-zip text-warning',
            '7z': 'bi-file-zip text-warning',
            // Media
            'mp3': 'bi-file-music text-info',
            'wav': 'bi-file-music text-info',
            'mp4': 'bi-file-play text-danger',
            'avi': 'bi-file-play text-danger',
            'mkv': 'bi-file-play text-danger',
            'mov': 'bi-file-play text-danger'
        };

        const iconClass = iconMap[ext] || 'bi-file-earmark file-icon-default';
        return `<i class="bi ${iconClass}"></i>`;
    }

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

    // API Functions
    async function loadFiles(path = '') {
        fileList.innerHTML = `
            <tr>
                <td colspan="4" class="text-center text-muted py-4">
                    <div class="spinner-border spinner-border-sm me-2"></div>
                    Cargando archivos...
                </td>
            </tr>
        `;

        try {
            const response = await fetch(`/files/api/list?path=${encodeURIComponent(path)}`);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Error al cargar archivos');
            }

            currentPath = data.current_path || '';
            renderFiles(data.items, data.parent_path);
            updateBreadcrumb(currentPath);
        } catch (error) {
            fileList.innerHTML = `
                <tr>
                    <td colspan="4" class="text-center text-danger py-4">
                        <i class="bi bi-exclamation-triangle me-2"></i>
                        ${error.message}
                    </td>
                </tr>
            `;
        }
    }

    function renderFiles(items, parentPath) {
        if (items.length === 0) {
            fileList.innerHTML = `
                <tr>
                    <td colspan="4" class="empty-state">
                        <i class="bi bi-folder2-open d-block"></i>
                        <p class="mb-0">Esta carpeta esta vacia</p>
                    </td>
                </tr>
            `;
            return;
        }

        let html = '';

        // Add parent directory link if not at root
        if (parentPath !== null && currentPath !== '') {
            html += `
                <tr class="file-item" data-path="${parentPath}" data-dir="true">
                    <td>
                        <span class="file-icon me-2">
                            <i class="bi bi-arrow-90deg-up text-muted"></i>
                        </span>
                        <span class="text-muted">..</span>
                    </td>
                    <td>-</td>
                    <td>-</td>
                    <td></td>
                </tr>
            `;
        }

        items.forEach(item => {
            html += `
                <tr class="file-item" data-path="${item.path}" data-dir="${item.is_dir}" data-name="${item.name}">
                    <td>
                        <span class="file-icon me-2">${getFileIcon(item.name, item.is_dir)}</span>
                        <span class="file-name">${item.name}</span>
                    </td>
                    <td class="text-muted">${item.size_formatted}</td>
                    <td class="text-muted small">${formatDate(item.modified)}</td>
                    <td class="text-end">
                        <div class="btn-group btn-group-sm">
                            ${!item.is_dir ? `
                            <a href="/files/api/download?path=${encodeURIComponent(item.path)}"
                               class="btn btn-outline-primary" title="Descargar">
                                <i class="bi bi-download"></i>
                            </a>
                            ` : ''}
                            <button class="btn btn-outline-secondary btn-rename" title="Renombrar">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button class="btn btn-outline-danger btn-delete" title="Eliminar">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        });

        fileList.innerHTML = html;
        attachRowEvents();
    }

    function updateBreadcrumb(path) {
        let html = `
            <li class="breadcrumb-item">
                <a href="#" data-path="" class="text-decoration-none">
                    <i class="bi bi-house-door"></i> Inicio
                </a>
            </li>
        `;

        if (path) {
            const parts = path.split('/');
            let accumulated = '';

            parts.forEach((part, index) => {
                accumulated += (accumulated ? '/' : '') + part;
                const isLast = index === parts.length - 1;

                if (isLast) {
                    html += `<li class="breadcrumb-item active">${part}</li>`;
                } else {
                    html += `
                        <li class="breadcrumb-item">
                            <a href="#" data-path="${accumulated}" class="text-decoration-none">${part}</a>
                        </li>
                    `;
                }
            });
        }

        breadcrumb.innerHTML = html;

        // Attach breadcrumb click events
        breadcrumb.querySelectorAll('a[data-path]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                loadFiles(link.dataset.path);
            });
        });
    }

    function attachRowEvents() {
        // Double-click to open folder
        fileList.querySelectorAll('.file-item').forEach(row => {
            row.addEventListener('dblclick', () => {
                if (row.dataset.dir === 'true') {
                    loadFiles(row.dataset.path);
                }
            });

            // Rename button
            const renameBtn = row.querySelector('.btn-rename');
            if (renameBtn) {
                renameBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    document.getElementById('rename-path').value = row.dataset.path;
                    document.getElementById('rename-input').value = row.dataset.name;
                    renameModal.show();
                });
            }

            // Delete button
            const deleteBtn = row.querySelector('.btn-delete');
            if (deleteBtn) {
                deleteBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    document.getElementById('delete-path').value = row.dataset.path;
                    document.getElementById('delete-filename').textContent = row.dataset.name;
                    deleteModal.show();
                });
            }
        });
    }

    // Action Functions
    async function createFolder() {
        const name = document.getElementById('new-folder-name').value.trim();
        if (!name) {
            showToast('Ingresa un nombre para la carpeta', 'warning');
            return;
        }

        try {
            const response = await fetch('/files/api/mkdir', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: currentPath, name: name })
            });

            const data = await response.json();

            if (response.ok) {
                showToast('Carpeta creada', 'success');
                newFolderModal.hide();
                document.getElementById('new-folder-name').value = '';
                loadFiles(currentPath);
            } else {
                showToast(data.error || 'Error', 'danger');
            }
        } catch (error) {
            showToast('Error de conexion', 'danger');
        }
    }

    async function renameItem() {
        const path = document.getElementById('rename-path').value;
        const newName = document.getElementById('rename-input').value.trim();

        if (!newName) {
            showToast('Ingresa un nuevo nombre', 'warning');
            return;
        }

        try {
            const response = await fetch('/files/api/rename', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: path, new_name: newName })
            });

            const data = await response.json();

            if (response.ok) {
                showToast('Renombrado correctamente', 'success');
                renameModal.hide();
                loadFiles(currentPath);
            } else {
                showToast(data.error || 'Error', 'danger');
            }
        } catch (error) {
            showToast('Error de conexion', 'danger');
        }
    }

    async function deleteItem() {
        const path = document.getElementById('delete-path').value;

        try {
            const response = await fetch('/files/api/delete', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: path })
            });

            const data = await response.json();

            if (response.ok) {
                showToast('Eliminado correctamente', 'success');
                deleteModal.hide();
                loadFiles(currentPath);
            } else {
                showToast(data.error || 'Error', 'danger');
            }
        } catch (error) {
            showToast('Error de conexion', 'danger');
        }
    }

    // Event Listeners
    document.getElementById('btn-new-folder').addEventListener('click', () => {
        document.getElementById('new-folder-name').value = '';
        newFolderModal.show();
    });

    document.getElementById('btn-create-folder').addEventListener('click', createFolder);
    document.getElementById('btn-confirm-rename').addEventListener('click', renameItem);
    document.getElementById('btn-confirm-delete').addEventListener('click', deleteItem);

    // Enter key in modals
    document.getElementById('new-folder-name').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') createFolder();
    });

    document.getElementById('rename-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') renameItem();
    });

    // Expose for upload.js
    window.FileBrowser = {
        getCurrentPath: () => currentPath,
        refresh: () => loadFiles(currentPath)
    };

    // Initial load
    loadFiles();
})();
