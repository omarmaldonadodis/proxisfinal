# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('/Users/omarmaldonado/Desktop/joseph-proxis/apuestas-backend/agente/agent/build/config.json.template', '.')]
binaries = []
hiddenimports = ['pystray._darwin', 'PIL._tkinter_finder']
tmp_ret = collect_all('pystray')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['/Users/omarmaldonado/Desktop/joseph-proxis/apuestas-backend/agente/agent/main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AdsPowerAgent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['/Users/omarmaldonado/Desktop/joseph-proxis/apuestas-backend/agente/agent/build/icon.ico'],
)
app = BUNDLE(
    exe,
    name='AdsPowerAgent.app',
    icon='/Users/omarmaldonado/Desktop/joseph-proxis/apuestas-backend/agente/agent/build/icon.ico',
    bundle_identifier=None,
)
