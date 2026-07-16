# -*- mode: python ; coding: utf-8 -*-
"""
TrustSync — PyInstaller Build Specification

Gera uma distribuição standalone em modo 'one-folder' (onedir),
incluindo os modelos ONNX, binários externos (exiftool.exe) e assets.
"""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Diretório raiz do projeto TrustSync
project_root = Path(SPECPATH).resolve()

# Dados adicionais a serem copiados para dentro da pasta do executável
datas = [
    (str(project_root / 'src' / 'models'), 'src/models'),
    (str(project_root / 'src' / 'bin'), 'src/bin'),
]

# Coletar arquivos de dados de bibliotecas complexas como librosa e onnxruntime
datas += collect_data_files('librosa')
datas += collect_data_files('onnxruntime', include_py_files=False)

# Imports ocultos necessários para introspecção dinâmica ou plugins Qt/PySide6
hiddenimports = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'onnxruntime',
    'openvino',
    'librosa',
    'soundfile',
    'cv2',
    'PIL',
] + collect_submodules('src')

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TrustSync',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # False para aplicação GUI sem janela de console separada
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Você pode adicionar o path para um ícone .ico aqui posteriormente
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TrustSync',
)
