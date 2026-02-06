// Dashboard JavaScript - Server Status & Controls

(function() {
    'use strict';

    // DOM Elements
    const serverStatus = document.getElementById('server-status');
    const diskUsage = document.getElementById('disk-usage');
    const diskProgress = document.getElementById('disk-progress');
    const diskUsed = document.getElementById('disk-used');
    const diskFree = document.getElementById('disk-free');
    const diskTotal = document.getElementById('disk-total');
    const nfsStatus = document.getElementById('nfs-status');

    const btnWake = document.getElementById('btn-wake');
    const btnShutdown = document.getElementById('btn-shutdown');
    const btnMount = document.getElementById('btn-mount');
    const btnUnmount = document.getElementById('btn-unmount');

    // State
    let isPolling = true;
    let pollInterval = null;

    // Utility Functions
    function formatBytes(bytes) {
        if (bytes === 0 || bytes === null) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    function showToast(message, type = 'info') {
        // Simple toast using Bootstrap
        const toastHtml = `
            <div class="toast align-items-center text-white bg-${type} border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;

        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(container);
        }

        container.insertAdjacentHTML('beforeend', toastHtml);
        const toast = container.lastElementChild;
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();

        toast.addEventListener('hidden.bs.toast', () => toast.remove());
    }

    // API Functions
    async function fetchStatus() {
        try {
            const response = await fetch('/api/server/status');
            if (!response.ok) throw new Error('Error de red');
            return await response.json();
        } catch (error) {
            console.error('Error fetching status:', error);
            return null;
        }
    }

    async function sendWake() {
        btnWake.disabled = true;
        btnWake.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Enviando...';

        try {
            const response = await fetch('/api/server/wake', { method: 'POST' });
            const data = await response.json();

            if (data.success) {
                showToast(data.message, 'success');
            } else {
                showToast(data.message || 'Error', 'danger');
            }
        } catch (error) {
            showToast('Error de conexion', 'danger');
        }

        btnWake.disabled = false;
        btnWake.innerHTML = '<i class="bi bi-power me-1"></i>Encender';
    }

    async function sendShutdown() {
        if (!confirm('¿Seguro que deseas apagar el servidor?')) return;

        btnShutdown.disabled = true;
        btnShutdown.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Apagando...';

        try {
            const response = await fetch('/api/server/shutdown', { method: 'POST' });
            const data = await response.json();

            if (data.success) {
                showToast(data.message, 'success');
            } else {
                showToast(data.message || 'Error', 'danger');
            }
        } catch (error) {
            showToast('Error de conexion', 'danger');
        }

        btnShutdown.disabled = false;
        btnShutdown.innerHTML = '<i class="bi bi-stop-circle me-1"></i>Apagar';
    }

    async function mountNfs() {
        btnMount.disabled = true;
        btnMount.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Montando...';

        try {
            const response = await fetch('/api/server/mount', { method: 'POST' });
            const data = await response.json();

            if (data.success) {
                showToast(data.message, 'success');
            } else {
                showToast(data.message || 'Error', 'danger');
            }
        } catch (error) {
            showToast('Error de conexion', 'danger');
        }

        btnMount.disabled = false;
        btnMount.innerHTML = '<i class="bi bi-link me-1"></i>Montar';
        updateStatus();
    }

    async function unmountNfs() {
        btnUnmount.disabled = true;
        btnUnmount.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Desmontando...';

        try {
            const response = await fetch('/api/server/unmount', { method: 'POST' });
            const data = await response.json();

            if (data.success) {
                showToast(data.message, 'success');
            } else {
                showToast(data.message || 'Error', 'danger');
            }
        } catch (error) {
            showToast('Error de conexion', 'danger');
        }

        btnUnmount.disabled = false;
        btnUnmount.innerHTML = '<i class="bi bi-link-45deg me-1"></i>Desmontar';
        updateStatus();
    }

    // UI Update Functions
    function updateStatus() {
        fetchStatus().then(status => {
            if (!status) {
                serverStatus.innerHTML = `
                    <span class="status-indicator status-offline"></span>
                    <span class="text-danger">Error al verificar estado</span>
                `;
                return;
            }

            if (status.online) {
                serverStatus.innerHTML = `
                    <span class="status-indicator status-online"></span>
                    <span class="text-success fw-bold">En Linea</span>
                    <span class="text-muted ms-2">(${status.ip})</span>
                `;

                btnWake.disabled = true;
                if (btnShutdown) btnShutdown.disabled = false;
                btnMount.disabled = status.nfs_mounted;
                btnUnmount.disabled = !status.nfs_mounted;

                // Update disk usage - show user quota if available
                if (status.user_quota) {
                    // User has quota - show their personal limits
                    diskUsage.classList.remove('d-none');
                    const used = status.user_quota.used_bytes;
                    const limit = status.user_quota.limit_bytes;
                    const percent = limit > 0 ? Math.round((used / limit) * 100) : 0;

                    diskProgress.style.width = percent + '%';
                    diskProgress.textContent = percent + '%';
                    diskProgress.className = 'progress-bar';

                    if (percent > 90) {
                        diskProgress.classList.add('bg-danger');
                    } else if (percent > 70) {
                        diskProgress.classList.add('bg-warning');
                    } else {
                        diskProgress.classList.add('bg-success');
                    }

                    diskUsed.textContent = 'Usado: ' + formatBytes(used);
                    diskFree.textContent = 'Libre: ' + formatBytes(limit - used);
                    diskTotal.textContent = 'Tu cuota: ' + formatBytes(limit);
                } else if (status.disk_total) {
                    // Admin or no quota - show total disk
                    diskUsage.classList.remove('d-none');
                    const percent = status.disk_used_percent || 0;

                    diskProgress.style.width = percent + '%';
                    diskProgress.textContent = percent + '%';
                    diskProgress.className = 'progress-bar';

                    if (percent > 90) {
                        diskProgress.classList.add('bg-danger');
                    } else if (percent > 70) {
                        diskProgress.classList.add('bg-warning');
                    } else {
                        diskProgress.classList.add('bg-success');
                    }

                    diskUsed.textContent = 'Usado: ' + formatBytes(status.disk_used);
                    diskFree.textContent = 'Libre: ' + formatBytes(status.disk_free);
                    diskTotal.textContent = 'Total: ' + formatBytes(status.disk_total);
                }
            } else {
                serverStatus.innerHTML = `
                    <span class="status-indicator status-offline"></span>
                    <span class="text-secondary">Apagado</span>
                `;

                btnWake.disabled = false;
                if (btnShutdown) btnShutdown.disabled = true;
                btnMount.disabled = true;
                btnUnmount.disabled = true;
                diskUsage.classList.add('d-none');
            }

            // Update NFS status
            if (status.nfs_mounted) {
                nfsStatus.innerHTML = `
                    <span class="status-indicator status-online"></span>
                    <span class="text-success">Montado</span>
                `;
            } else {
                nfsStatus.innerHTML = `
                    <span class="status-indicator status-offline"></span>
                    <span class="text-secondary">No montado</span>
                `;
            }
        });
    }

    // Event Listeners
    btnWake.addEventListener('click', sendWake);
    if (btnShutdown) btnShutdown.addEventListener('click', sendShutdown);
    btnMount.addEventListener('click', mountNfs);
    btnUnmount.addEventListener('click', unmountNfs);

    // Start polling
    updateStatus();
    pollInterval = setInterval(updateStatus, 5000);

    // Stop polling when page is hidden
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            clearInterval(pollInterval);
        } else {
            updateStatus();
            pollInterval = setInterval(updateStatus, 5000);
        }
    });
})();
