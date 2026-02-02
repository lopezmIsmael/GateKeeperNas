from flask import current_app
from app.services.ssh import execute_remote


class QuotaService:
    @staticmethod
    def create_user_on_server(username: str) -> bool:
        """Create a system user on the server for quota management."""
        # Check if user exists
        stdout, stderr, code = execute_remote(f'id {username}')
        if code == 0:
            current_app.logger.info(f"User {username} already exists on server")
            return True

        # Create user without login shell
        stdout, stderr, code = execute_remote(
            f'useradd -M -s /usr/sbin/nologin {username}',
            sudo=True
        )
        if code != 0:
            current_app.logger.error(f"Failed to create user on server: {stderr}")
            return False

        return True

    @staticmethod
    def create_user_directory(username: str) -> bool:
        """Create user's data directory on the server."""
        mount_point = current_app.config['QUOTA_MOUNT_POINT']
        user_dir = f"{mount_point}/{username}"

        # Create directory
        stdout, stderr, code = execute_remote(f'mkdir -p {user_dir}', sudo=True)
        if code != 0:
            current_app.logger.error(f"Failed to create directory: {stderr}")
            return False

        # Set ownership
        stdout, stderr, code = execute_remote(f'chown {username}:{username} {user_dir}', sudo=True)
        if code != 0:
            current_app.logger.error(f"Failed to set ownership: {stderr}")
            return False

        # Set permissions (only user can access)
        stdout, stderr, code = execute_remote(f'chmod 700 {user_dir}', sudo=True)
        if code != 0:
            current_app.logger.error(f"Failed to set permissions: {stderr}")
            return False

        return True

    @staticmethod
    def set_quota(username: str, quota_gb: int) -> bool:
        """Set disk quota for a user."""
        mount_point = current_app.config['QUOTA_MOUNT_POINT']

        # Convert GB to blocks (1 block = 1KB for most systems)
        soft_limit = quota_gb * 1024 * 1024  # GB to KB
        hard_limit = soft_limit  # Same as soft limit for strict enforcement

        stdout, stderr, code = execute_remote(
            f'setquota -u {username} {soft_limit} {hard_limit} 0 0 {mount_point}',
            sudo=True
        )

        if code != 0:
            current_app.logger.error(f"Failed to set quota: {stderr}")
            return False

        current_app.logger.info(f"Quota set for {username}: {quota_gb}GB")
        return True

    @staticmethod
    def get_quota(username: str) -> dict | None:
        """Get quota information for a user."""
        mount_point = current_app.config['QUOTA_MOUNT_POINT']

        stdout, stderr, code = execute_remote(
            f'quota -u {username} -w 2>/dev/null | tail -1'
        )

        if code != 0 or not stdout:
            return None

        parts = stdout.split()
        if len(parts) < 4:
            return None

        try:
            return {
                'used_kb': int(parts[1].rstrip('*')),
                'soft_limit_kb': int(parts[2]),
                'hard_limit_kb': int(parts[3]),
                'used_gb': int(parts[1].rstrip('*')) / (1024 * 1024),
                'limit_gb': int(parts[3]) / (1024 * 1024)
            }
        except (ValueError, IndexError):
            return None

    @staticmethod
    def remove_user(username: str) -> bool:
        """Remove user and their quota from the server."""
        mount_point = current_app.config['QUOTA_MOUNT_POINT']
        user_dir = f"{mount_point}/{username}"

        # Remove quota
        execute_remote(f'setquota -u {username} 0 0 0 0 {mount_point}', sudo=True)

        # Remove user directory (be careful!)
        stdout, stderr, code = execute_remote(f'rm -rf {user_dir}', sudo=True)
        if code != 0:
            current_app.logger.warning(f"Failed to remove user directory: {stderr}")

        # Remove system user
        stdout, stderr, code = execute_remote(f'userdel {username}', sudo=True)
        if code != 0:
            current_app.logger.warning(f"Failed to remove system user: {stderr}")

        return True

    @staticmethod
    def setup_new_user(username: str, quota_gb: int) -> bool:
        """Complete setup for a new user on the server."""
        if not QuotaService.create_user_on_server(username):
            return False

        if not QuotaService.create_user_directory(username):
            return False

        if not QuotaService.set_quota(username, quota_gb):
            return False

        return True
