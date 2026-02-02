import subprocess
import os
from flask import current_app


class NFSService:
    @staticmethod
    def is_mounted() -> bool:
        """Check if NFS share is currently mounted."""
        mount_point = current_app.config['NFS_MOUNT_POINT']
        try:
            result = subprocess.run(
                ['mountpoint', '-q', mount_point],
                capture_output=True
            )
            return result.returncode == 0
        except Exception as e:
            current_app.logger.error(f"Mount check failed: {e}")
            return False

    @staticmethod
    def mount() -> bool:
        """Mount the NFS share."""
        mount_point = current_app.config['NFS_MOUNT_POINT']
        nfs_export = current_app.config['NFS_EXPORT']

        if NFSService.is_mounted():
            current_app.logger.info("NFS already mounted")
            return True

        # Ensure mount point exists
        try:
            os.makedirs(mount_point, exist_ok=True)
        except PermissionError:
            current_app.logger.error(f"Cannot create mount point {mount_point}")
            return False

        try:
            result = subprocess.run(
                ['sudo', 'mount', '-t', 'nfs', '-o', 'soft,timeo=10', nfs_export, mount_point],
                capture_output=True,
                timeout=30
            )
            if result.returncode == 0:
                current_app.logger.info(f"NFS mounted at {mount_point}")
                return True
            else:
                current_app.logger.error(f"Mount failed: {result.stderr.decode()}")
                return False
        except subprocess.TimeoutExpired:
            current_app.logger.error("Mount timed out")
            return False
        except Exception as e:
            current_app.logger.error(f"Mount exception: {e}")
            return False

    @staticmethod
    def unmount() -> bool:
        """Unmount the NFS share."""
        mount_point = current_app.config['NFS_MOUNT_POINT']

        if not NFSService.is_mounted():
            current_app.logger.info("NFS not mounted")
            return True

        try:
            result = subprocess.run(
                ['sudo', 'umount', mount_point],
                capture_output=True,
                timeout=30
            )
            if result.returncode == 0:
                current_app.logger.info(f"NFS unmounted from {mount_point}")
                return True
            else:
                current_app.logger.error(f"Unmount failed: {result.stderr.decode()}")
                return False
        except Exception as e:
            current_app.logger.error(f"Unmount exception: {e}")
            return False

    @staticmethod
    def get_user_path(username: str) -> str:
        """Get the full path to a user's directory on NFS."""
        return os.path.join(current_app.config['NFS_MOUNT_POINT'], username)

    @staticmethod
    def ensure_user_directory(username: str) -> bool:
        """Ensure user directory exists on NFS mount."""
        user_path = NFSService.get_user_path(username)
        try:
            os.makedirs(user_path, exist_ok=True)
            return True
        except Exception as e:
            current_app.logger.error(f"Failed to create user directory: {e}")
            return False
