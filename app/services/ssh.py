import paramiko
from flask import current_app


class SSHService:
    def __init__(self):
        self._client = None

    def _get_config(self):
        return {
            'hostname': current_app.config['SERVER_IP'],
            'port': current_app.config['SSH_PORT'],
            'username': current_app.config['SSH_USER'],
            'key_filename': current_app.config['SSH_KEY_PATH'],
            'timeout': current_app.config['SSH_TIMEOUT']
        }

    def connect(self):
        if self._client is not None:
            return True

        try:
            self._client = paramiko.SSHClient()
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._client.connect(**self._get_config())
            return True
        except Exception as e:
            current_app.logger.error(f"SSH connection failed: {e}")
            self._client = None
            return False

    def disconnect(self):
        if self._client:
            self._client.close()
            self._client = None

    def execute(self, command: str) -> tuple[str, str, int]:
        """
        Execute a command on the remote server.

        Returns:
            tuple: (stdout, stderr, exit_code)
        """
        if not self.connect():
            return '', 'SSH connection failed', -1

        try:
            stdin, stdout, stderr = self._client.exec_command(command)
            exit_code = stdout.channel.recv_exit_status()
            return (
                stdout.read().decode('utf-8').strip(),
                stderr.read().decode('utf-8').strip(),
                exit_code
            )
        except Exception as e:
            current_app.logger.error(f"SSH command execution failed: {e}")
            return '', str(e), -1

    def execute_sudo(self, command: str) -> tuple[str, str, int]:
        """Execute a command with sudo privileges."""
        return self.execute(f'sudo {command}')

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


def execute_remote(command: str, sudo: bool = False) -> tuple[str, str, int]:
    """Convenience function for one-off command execution."""
    with SSHService() as ssh:
        if sudo:
            return ssh.execute_sudo(command)
        return ssh.execute(command)
