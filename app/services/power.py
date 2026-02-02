import subprocess
import time
from wakeonlan import send_magic_packet
from flask import current_app

from app.services.ssh import execute_remote


class PowerService:
    @staticmethod
    def ping(ip: str = None, timeout: int = None) -> bool:
        """Check if server is reachable via ping."""
        if ip is None:
            ip = current_app.config['SERVER_IP']
        if timeout is None:
            timeout = current_app.config['PING_TIMEOUT']

        try:
            result = subprocess.run(
                ['ping', '-c', '1', '-W', str(timeout), ip],
                capture_output=True,
                timeout=timeout + 1
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False
        except Exception as e:
            current_app.logger.error(f"Ping failed: {e}")
            return False

    @staticmethod
    def send_wol(mac: str = None, broadcast: str = None) -> bool:
        """Send Wake-on-LAN magic packet."""
        if mac is None:
            mac = current_app.config['SERVER_MAC']
        if broadcast is None:
            broadcast = current_app.config['SERVER_BROADCAST']

        try:
            send_magic_packet(mac, ip_address=broadcast)
            current_app.logger.info(f"WoL packet sent to {mac}")
            return True
        except Exception as e:
            current_app.logger.error(f"WoL failed: {e}")
            return False

    @staticmethod
    def wake_and_wait(timeout: int = None) -> bool:
        """Send WoL and wait for server to come online."""
        if timeout is None:
            timeout = current_app.config['WOL_WAIT_TIME']

        if not PowerService.send_wol():
            return False

        start_time = time.time()
        while time.time() - start_time < timeout:
            if PowerService.ping():
                current_app.logger.info("Server is now online")
                return True
            time.sleep(2)

        current_app.logger.warning("Server did not come online within timeout")
        return False

    @staticmethod
    def shutdown() -> bool:
        """Shutdown the server via SSH."""
        stdout, stderr, code = execute_remote('poweroff', sudo=True)
        if code == 0 or code == -1:  # -1 can happen when connection drops during shutdown
            current_app.logger.info("Server shutdown command sent")
            return True
        current_app.logger.error(f"Shutdown failed: {stderr}")
        return False

    @staticmethod
    def get_status() -> dict:
        """Get comprehensive server status."""
        is_online = PowerService.ping()

        status = {
            'online': is_online,
            'ip': current_app.config['SERVER_IP'],
            'disk_free': None,
            'disk_total': None,
            'disk_used_percent': None
        }

        if is_online:
            # Get disk usage
            stdout, stderr, code = execute_remote(
                f"df -B1 {current_app.config['QUOTA_MOUNT_POINT']} | tail -1"
            )
            if code == 0 and stdout:
                parts = stdout.split()
                if len(parts) >= 4:
                    status['disk_total'] = int(parts[1])
                    status['disk_used'] = int(parts[2])
                    status['disk_free'] = int(parts[3])
                    status['disk_used_percent'] = int(parts[4].rstrip('%'))

        return status
