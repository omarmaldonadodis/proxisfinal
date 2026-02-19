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

    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",          # sin consola
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

    if system == "Darwin":
        cmd.extend(["--target-arch", "universal2"])  # Intel + Apple Silicon

    subprocess.run(cmd, check=True, cwd=str(ROOT))
    print(f"✅ Ejecutable generado en: {DIST_DIR}")


if __name__ == "__main__":
    build()