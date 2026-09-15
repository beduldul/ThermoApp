# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec untuk membangun ThermoApp engine runner mandiri.

Menghasilkan onefile binary (darwin-64) yang mengemas:
  - engine_cli + thermoapp engine
  - seluruh dependency (pycalphad, numpy, scipy, matplotlib, dll)
  - file data TDB milik pycalphad (via collect_data_files dari paket pycalphad)
"""
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Kumpulkan semua file data .tdb dan data lain dari pycalphad
datas = collect_data_files("pycalphad", include_py_files=False)
# Tambahkan source thermoapp + engine_cli ke bundle (folder 'src' dan file)
project_root = r"/Users/abdulafifalkaysan/Documents/factsage macos/thermoapp"
datas += [
    (project_root + "/engine_cli.py", "."),
    (project_root + "/src", "src"),
]

# Pastikan semua submodule numerik & plotting tersedia (pyinstaller kadang melewatkan)
hiddenimports = collect_submodules("scipy") + collect_submodules("matplotlib")

a = Analysis(
    [project_root + "/native/engine_runner.py"],
    pathex=[project_root, project_root + "/native", project_root + "/src"],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "PyQt5", "PySide2"],
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
    name="engine_runner",
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
)
