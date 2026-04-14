# agent/build/build.py
"""
Genera el ejecutable final con PyInstaller.
Ejecutar desde la raíz del proyecto: python agent/build/build.py
"""
import subprocess
import sys
import platform
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent  # raíz del proyecto
AGENT_DIR = ROOT / "agent"
DIST_DIR = ROOT / "dist"


def build():
    system = platform.system()
    print(f"🔨 Building para {system}...")

    cmd = ["python3", "-m", "PyInstaller"]
    if system == "Windows":
        cmd.append("--uac-admin")

    cmd += [
        "--onefile",
        "--hidden-import", "websockets.legacy.client",
        "--hidden-import", "websockets.legacy.server", 
        "--hidden-import", "httpx._transports.default",
        "--hidden-import", "loguru",
        "--hidden-import", "psutil",
        "--name", "AdsPowerAgent",
        "--icon", str(AGENT_DIR / "build" / "icon.ico"),
        "--add-data", f"{AGENT_DIR / 'build' / 'config.json.template'}{':' if system != 'Windows' else ';'}.",
        "--hidden-import", "pystray._win32" if system == "Windows" else (
            "pystray._darwin" if system == "Darwin" else "pystray._xorg"
        ),
        "--hidden-import", "PIL._tkinter_finder",
        "--collect-all", "pystray",
        str(AGENT_DIR / "main.py")
    ]

    subprocess.run(cmd, check=True, cwd=str(ROOT))
    print(f"✅ Ejecutable generado en: {DIST_DIR}")


if __name__ == "__main__":
    build()