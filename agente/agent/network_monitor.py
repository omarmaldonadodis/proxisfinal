# agent/network_monitor.py
"""
Mide el consumo de red de la computadora.
Calcula velocidad actual y consumo acumulado por sesión.
"""
import psutil
import time
from typing import Dict
from loguru import logger


class NetworkMonitor:

    def __init__(self):
        self._last_stats = psutil.net_io_counters()
        self._last_time = time.time()

        # Punto de inicio de la sesión actual
        self._session_start = self._last_stats
        self._session_start_time = self._last_time

    def get_stats(self) -> Dict:
        """
        Retorna velocidad actual (KB/s) y consumo de sesión (MB).
        Llamar periódicamente para obtener datos precisos.
        """
        now = time.time()
        current = psutil.net_io_counters()
        elapsed = now - self._last_time

        if elapsed < 0.1:
            elapsed = 0.1

        # Velocidad actual
        upload_speed_kbps = (
            (current.bytes_sent - self._last_stats.bytes_sent) / elapsed / 1024
        )
        download_speed_kbps = (
            (current.bytes_recv - self._last_stats.bytes_recv) / elapsed / 1024
        )

        # Consumo total desde inicio de sesión
        session_sent_mb = (
            (current.bytes_sent - self._session_start.bytes_sent) / (1024 * 1024)
        )
        session_recv_mb = (
            (current.bytes_recv - self._session_start.bytes_recv) / (1024 * 1024)
        )

        # Guardar para próxima llamada
        self._last_stats = current
        self._last_time = now

        return {
            "upload_speed_kbps": round(max(0, upload_speed_kbps), 2),
            "download_speed_kbps": round(max(0, download_speed_kbps), 2),
            "session_sent_mb": round(max(0, session_sent_mb), 3),
            "session_received_mb": round(max(0, session_recv_mb), 3),
            "session_total_mb": round(max(0, session_sent_mb + session_recv_mb), 3)
        }

    def reset_session(self):
        """Resetear el contador de sesión (al abrir un nuevo navegador)"""
        self._session_start = psutil.net_io_counters()
        self._session_start_time = time.time()
        logger.debug("Network monitor: sesión reseteada")

    def get_system_stats(self) -> Dict:
        """Stats generales del sistema"""
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return {
            "cpu_percent": round(cpu, 1),
            "ram_percent": round(ram.percent, 1),
            "ram_used_mb": round(ram.used / (1024 * 1024), 1),
            "ram_total_mb": round(ram.total / (1024 * 1024), 1),
            "disk_percent": round(disk.percent, 1)
        }