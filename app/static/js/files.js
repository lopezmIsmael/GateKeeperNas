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
    const previewModal = new bootstrap.Modal(document.getElementById('previewModal'));
    const infoModal = new bootstrap.Modal(document.getElementById('infoModal'));

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
            'bmp': 'bi-file-image text-success',
            'ico': 'bi-file-image text-success',
            // Documents
            'pdf': 'bi-file-pdf text-danger',
            'doc': 'bi-file-word text-primary',
            'docx': 'bi-file-word text-primary',
            'xls': 'bi-file-excel text-success',
            'xlsx': 'bi-file-excel text-success',
            'ppt': 'bi-file-ppt text-warning',
            'pptx': 'bi-file-ppt text-warning',
            'txt': 'bi-file-text',
            'md': 'bi-markdown text-info',
            // Code
            'js': 'bi-file-code text-warning',
            'py': 'bi-file-code text-info',
            'html': 'bi-file-code text-danger',
            'css': 'bi-file-code text-primary',
            'json': 'bi-file-code text-warning',
            'xml': 'bi-file-code text-warning',
            'yaml': 'bi-file-code text-info',
            'yml': 'bi-file-code text-info',
            // Archives
            'zip': 'bi-file-zip text-warning',
            'rar': 'bi-file-zip text-warning',
            'tar': 'bi-file-zip text-warning',
            'gz': 'bi-file-zip text-warning',
            '7z': 'bi-file-zip text-warning',
            // Media
            'mp3': 'bi-file-music text-info',
            'wav': 'bi-file-music text-info',
            'flac': 'bi-file-music text-info',
            'ogg': 'bi-file-music text-info',
            'mp4': 'bi-file-play text-danger',
            'avi': 'bi-file-play text-danger',
            'mkv': 'bi-file-play text-danger',
            'mov': 'bi-file-play text-danger',
            'webm': 'bi-file-play text-danger'
        };

        const iconClass = iconMap[ext] || 'bi-file-earmark file-icon-default';
        return `<i class="bi ${iconClass}"></i>`;
    }
    
    function getFileType(filename, mimeType) {
        if (!mimeType) return 'Archivo';
        
        const ext = filename.split('.').pop().toLowerCase();
        
        // Map common types to Spanish
        const typeMap = {
            'image': 'Imagen',
            'video': 'Video',
            'audio': 'Audio',
            'text': 'Texto',
            'application/pdf': 'PDF',
            'application/zip': 'Archivo',
            'application/x-rar': 'Archivo',
            'application/vnd.ms-word': 'Word',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'Word',
            'application/vnd.ms-excel': 'Excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'Excel',
            'application/vnd.ms-powerpoint': 'PowerPoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'PowerPoint'
        };
        
        // Check exact match first
        if (typeMap[mimeType]) return typeMap[mimeType];
        
        // Check by prefix
        for (const [key, value] of Object.entries(typeMap)) {
            if (mimeType.startsWith(key)) return value;
        }
        
        // Fallback to extension
        return ext.toUpperCase();
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
                <td colspan="5" class="text-center text-muted py-4">
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
                    <td colspan="5" class="text-center text-danger py-4">
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
                    <td colspan="5" class="empty-state">
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
                    <td>-</td>
                    <td></td>
                </tr>
            `;
        }

        items.forEach(item => {
            const fileType = item.is_dir ? 'Carpeta' : getFileType(item.name, item.mime_type);
            const canPreview = !item.is_dir && isPreviewable(item.name, item.mime_type);
            
            html += `
                <tr class="file-item" data-path="${item.path}" data-dir="${item.is_dir}" 
                    data-name="${item.name}" data-mime="${item.mime_type || ''}">
                    <td>
                        <span class="file-icon me-2">${getFileIcon(item.name, item.is_dir)}</span>
                        <span class="file-name">${item.name}</span>
                    </td>
                    <td class="text-muted">${item.size_formatted}</td>
                    <td class="text-muted small">${fileType}</td>
                    <td class="text-muted small">${formatDate(item.modified)}</td>
                    <td class="text-end">
                        <div class="btn-group btn-group-sm">
                            ${!item.is_dir && canPreview ? `
                            <button class="btn btn-outline-info btn-preview" title="Previsualizar">
                                <i class="bi bi-eye"></i>
                            </button>
                            ` : ''}
                            ${!item.is_dir ? `
                            <button class="btn btn-outline-secondary btn-info" title="Información">
                                <i class="bi bi-info-circle"></i>
                            </button>
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
    
    function isPreviewable(filename, mimeType) {
        // Check by MIME type first
        if (mimeType) {
            // Images, videos, audio, PDFs
            if (mimeType.startsWith('image/') || mimeType.startsWith('video/') || 
                mimeType.startsWith('audio/') || mimeType === 'application/pdf') {
                return true;
            }
            
            // Text files
            if (mimeType.startsWith('text/')) {
                return true;
            }
        }
        
        // Check by extension (fallback if no MIME type)
        const ext = filename.split('.').pop().toLowerCase();
        const previewableExts = ['md', 'txt', 'json', 'xml', 'csv', 'log', 
                                 'py', 'js', 'html', 'css', 'yaml', 'yml',
                                 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
                                 'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp', 'ico',
                                 'mp4', 'avi', 'mkv', 'mov', 'webm',
                                 'mp3', 'wav', 'flac', 'ogg',
                                 'pdf'];
        return previewableExts.includes(ext);
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
        // Double-click to open folder or preview file
        fileList.querySelectorAll('.file-item').forEach(row => {
            row.addEventListener('dblclick', () => {
                if (row.dataset.dir === 'true') {
                    loadFiles(row.dataset.path);
                } else {
                    // Preview file on double-click
                    previewFile(row.dataset.path);
                }
            });
            
            // Preview button
            const previewBtn = row.querySelector('.btn-preview');
            if (previewBtn) {
                previewBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    previewFile(row.dataset.path);
                });
            }
            
            // Info button
            const infoBtn = row.querySelector('.btn-info');
            if (infoBtn) {
                infoBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    showFileInfo(row.dataset.path);
                });
            }

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
    
    // File Preview Functions
    async function previewFile(path) {
        const previewBody = document.getElementById('preview-body');
        const previewFilename = document.getElementById('preview-filename');
        const previewSubtitle = document.getElementById('preview-subtitle');
        const previewMetadata = document.getElementById('preview-metadata');
        const downloadBtn = document.getElementById('preview-download-btn');
        
        // Reset modal
        previewBody.innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Cargando...</span>
                </div>
                <p class="mt-3 text-muted">Cargando previsualizacion...</p>
            </div>
        `;
        previewFilename.textContent = 'Cargando...';
        previewSubtitle.textContent = '';
        previewMetadata.textContent = '';
        
        // Set download link
        downloadBtn.href = `/files/api/download?path=${encodeURIComponent(path)}`;
        
        previewModal.show();
        
        try {
            // Get file info first
            const infoResponse = await fetch(`/files/api/file-info?path=${encodeURIComponent(path)}`);
            const fileInfo = await infoResponse.json();
            
            if (!infoResponse.ok) {
                throw new Error(fileInfo.error || 'Error al obtener informacion del archivo');
            }
            
            // Update header
            previewFilename.textContent = fileInfo.name;
            previewSubtitle.textContent = `${fileInfo.size_formatted} • ${fileInfo.mime_type || 'Desconocido'}`;
            previewMetadata.innerHTML = `
                <i class="bi bi-calendar me-1"></i> Subido: ${fileInfo.created_formatted}<br>
                <i class="bi bi-clock me-1"></i> Modificado: ${fileInfo.modified_formatted}
            `;
            
            // Render preview based on file type
            if (fileInfo.is_image) {
                renderImagePreview(path);
            } else if (fileInfo.is_video) {
                renderVideoPreview(path, fileInfo.mime_type);
            } else if (fileInfo.is_audio) {
                renderAudioPreview(path, fileInfo.mime_type);
            } else if (fileInfo.is_pdf) {
                renderPdfPreview(path);
            } else if (fileInfo.is_office) {
                renderOfficePreview(path, fileInfo.name);
            } else if (fileInfo.is_text || fileInfo.extension === '.md') {
                renderTextPreview(path, fileInfo.extension, fileInfo.name);
            } else {
                previewBody.innerHTML = `
                    <div class="text-center py-5">
                        <i class="bi bi-file-earmark-x fs-1 text-muted"></i>
                        <p class="mt-3 text-muted">No hay vista previa disponible para este tipo de archivo</p>
                        <p class="small text-muted">Puedes descargarlo usando el boton de abajo</p>
                    </div>
                `;
            }
            
        } catch (error) {
            previewBody.innerHTML = `
                <div class="text-center py-5 text-danger">
                    <i class="bi bi-exclamation-triangle fs-1"></i>
                    <p class="mt-3">${error.message}</p>
                </div>
            `;
        }
    }
    
    function renderImagePreview(path) {
        const previewBody = document.getElementById('preview-body');
        previewBody.innerHTML = `
            <div class="text-center p-4" style="background: #000;">
                <img src="/files/api/preview?path=${encodeURIComponent(path)}" 
                     class="img-fluid" 
                     style="max-height: 70vh; object-fit: contain;"
                     alt="Preview">
            </div>
        `;
    }
    
    function renderVideoPreview(path, mimeType) {
        const previewBody = document.getElementById('preview-body');
        previewBody.innerHTML = `
            <div class="p-4" style="background: #000;">
                <video controls class="w-100" style="max-height: 70vh;">
                    <source src="/files/api/preview?path=${encodeURIComponent(path)}" type="${mimeType}">
                    Tu navegador no soporta la reproduccion de video.
                </video>
            </div>
        `;
    }
    
    function renderAudioPreview(path, mimeType) {
        const previewBody = document.getElementById('preview-body');
        previewBody.innerHTML = `
            <div class="text-center p-5">
                <i class="bi bi-music-note-beamed fs-1 text-primary mb-4"></i>
                <audio controls class="w-100" style="max-width: 500px;">
                    <source src="/files/api/preview?path=${encodeURIComponent(path)}" type="${mimeType}">
                    Tu navegador no soporta la reproduccion de audio.
                </audio>
            </div>
        `;
    }
    
    function renderPdfPreview(path) {
        const previewBody = document.getElementById('preview-body');
        previewBody.innerHTML = `
            <div style="height: 70vh;">
                <iframe src="/files/api/preview?path=${encodeURIComponent(path)}" 
                        class="w-100 h-100 border-0">
                </iframe>
            </div>
        `;
    }
    
    function renderOfficePreview(path, filename) {
        const previewBody = document.getElementById('preview-body');
        const viewerUrl = `https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(window.location.origin + '/files/api/serve/' + encodeURIComponent(path))}`;
        
        previewBody.innerHTML = `
            <div style="height: 70vh;">
                <iframe src="${viewerUrl}" 
                        class="w-100 h-100 border-0">
                </iframe>
                <div class="text-center mt-3 small text-muted">
                    <i class="bi bi-info-circle me-1"></i>
                    Si la previsualizacion no carga, descarga el archivo para verlo
                </div>
            </div>
        `;
    }
    
    async function renderTextPreview(path, extension, filename) {
        const previewBody = document.getElementById('preview-body');
        
        try {
            const response = await fetch(`/files/api/preview?path=${encodeURIComponent(path)}`);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Error al cargar contenido');
            }
            
            let content = data.content;
            
            // Special handling for markdown
            if (extension === '.md') {
                content = marked.parse(content);
                previewBody.innerHTML = `
                    <div class="p-4 markdown-body" style="max-height: 70vh; overflow-y: auto;">
                        ${content}
                    </div>
                `;
            } else {
                // Detect language for syntax highlighting
                const lang = detectLanguage(extension);
                let highlightedCode = content;
                
                if (lang && window.hljs) {
                    try {
                        highlightedCode = hljs.highlight(content, { language: lang }).value;
                    } catch (e) {
                        // Fallback to plain text if highlighting fails
                        highlightedCode = content;
                    }
                }
                
                previewBody.innerHTML = `
                    <div class="p-0" style="max-height: 70vh; overflow-y: auto;">
                        <pre class="mb-0"><code class="hljs">${highlightedCode}</code></pre>
                    </div>
                `;
            }
            
        } catch (error) {
            previewBody.innerHTML = `
                <div class="text-center py-5 text-danger">
                    <i class="bi bi-exclamation-triangle fs-1"></i>
                    <p class="mt-3">${error.message}</p>
                </div>
            `;
        }
    }
    
    function detectLanguage(extension) {
        const langMap = {
            '.js': 'javascript',
            '.py': 'python',
            '.json': 'json',
            '.xml': 'xml',
            '.html': 'xml',
            '.css': 'css',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.sh': 'bash',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.go': 'go',
            '.rs': 'rust',
            '.php': 'php',
            '.rb': 'ruby',
            '.sql': 'sql'
        };
        return langMap[extension];
    }
    
    async function showFileInfo(path) {
        const infoBody = document.getElementById('info-body');
        
        infoBody.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-primary" role="status"></div>
            </div>
        `;
        
        infoModal.show();
        
        try {
            const response = await fetch(`/files/api/file-info?path=${encodeURIComponent(path)}`);
            const fileInfo = await response.json();
            
            if (!response.ok) {
                throw new Error(fileInfo.error || 'Error al obtener informacion');
            }
            
            infoBody.innerHTML = `
                <div class="row g-3">
                    <div class="col-12">
                        <div class="d-flex align-items-center mb-3">
                            <div class="fs-1 me-3">${getFileIcon(fileInfo.name, false)}</div>
                            <div>
                                <h6 class="mb-0">${fileInfo.name}</h6>
                                <small class="text-muted">${fileInfo.mime_type || 'Desconocido'}</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-12">
                        <hr class="my-2">
                    </div>
                    <div class="col-6">
                        <small class="text-muted d-block">Tamaño</small>
                        <strong>${fileInfo.size_formatted}</strong>
                        <small class="text-muted d-block">(${fileInfo.size.toLocaleString()} bytes)</small>
                    </div>
                    <div class="col-6">
                        <small class="text-muted d-block">Tipo</small>
                        <strong>${getFileType(fileInfo.name, fileInfo.mime_type)}</strong>
                    </div>
                    <div class="col-12">
                        <hr class="my-2">
                    </div>
                    <div class="col-12">
                        <small class="text-muted d-block"><i class="bi bi-calendar-plus me-1"></i>Fecha de subida</small>
                        <strong>${fileInfo.created_formatted}</strong>
                    </div>
                    <div class="col-12">
                        <small class="text-muted d-block"><i class="bi bi-clock-history me-1"></i>Última modificación</small>
                        <strong>${fileInfo.modified_formatted}</strong>
                    </div>
                    <div class="col-12">
                        <hr class="my-2">
                    </div>
                    <div class="col-12">
                        <small class="text-muted d-block">Ruta completa</small>
                        <code class="small">${fileInfo.path}</code>
                    </div>
                </div>
            `;
            
        } catch (error) {
            infoBody.innerHTML = `
                <div class="text-center py-4 text-danger">
                    <i class="bi bi-exclamation-triangle"></i>
                    <p class="mt-2 mb-0">${error.message}</p>
                </div>
            `;
        }
    }

    // Expose for upload.js
    window.FileBrowser = {
        getCurrentPath: () => currentPath,
        refresh: () => loadFiles(currentPath)
    };

    // Initial load
    loadFiles();
})();
