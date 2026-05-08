# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for POD Renamer - optimized for small size."""

import sys
from pathlib import Path

block_cipher = None

# Exclude heavy/unused PyQt5 modules
excluded_imports = [
    'PyQt5.QtWebEngine',
    'PyQt5.QtWebEngineCore',
    'PyQt5.QtWebEngineWidgets',
    'PyQt5.QtWebChannel',
    'PyQt5.QtWebSockets',
    'PyQt5.QtMultimedia',
    'PyQt5.QtMultimediaWidgets',
    'PyQt5.QtBluetooth',
    'PyQt5.QtNfc',
    'PyQt5.QtSerialPort',
    'PyQt5.QtPositioning',
    'PyQt5.QtLocation',
    'PyQt5.QtSensors',
    'PyQt5.QtQuick',
    'PyQt5.QtQuickWidgets',
    'PyQt5.QtQml',
    'PyQt5.QtSql',
    'PyQt5.QtXml',
    'PyQt5.QtXmlPatterns',
    'PyQt5.QtHelp',
    'PyQt5.QtTest',
    'PyQt5.QtDesigner',
    'PyQt5.QtDBus',
    'PyQt5.QtNetwork',
    'PyQt5.QtOpenGL',
    'PyQt5.QtPrintSupport',
    'PyQt5.QtSvg',
    'PyQt5.QtWinExtras',
    'PyQt5.QAxContainer',
    'PyQt5.QtDataVisualization',
    'PyQt5.QtChart',
    'PyQt5.QtTextToSpeech',
    'PyQt5.Qt3DCore',
    'PyQt5.Qt3DInput',
    'PyQt5.Qt3DLogic',
    'PyQt5.Qt3DRender',
    'PyQt5.Qt3DAnimation',
    'PyQt5.Qt3DExtras',
    'PyQt5.pyrcc',
    'PyQt5.uic',
    'numpy',
    'scipy',
    'matplotlib',
    'pandas',
    'cv2',
    'opencv',
    'tkinter',
    'unittest',
    'email',
    'http',
    'xmlrpc',
    'pydoc',
    'distutils',
    'setuptools',
    'pip',
]

# Exclude unused Qt5 DLLs from being bundled
excluded_binaries = [
    'Qt5Qml',
    'Qt5QmlModels',
    'Qt5QmlWorkerScript',
    'Qt5Quick',
    'Qt5QuickControls2',
    'Qt5QuickTemplates2',
    'Qt5QuickWidgets',
    'Qt5WebEngine',
    'Qt5WebEngineCore',
    'Qt5WebChannel',
    'Qt5WebSockets',
    'Qt5Multimedia',
    'Qt5MultimediaWidgets',
    'Qt5Bluetooth',
    'Qt5Nfc',
    'Qt5SerialPort',
    'Qt5Positioning',
    'Qt5Location',
    'Qt5Sensors',
    'Qt5Sql',
    'Qt5Xml',
    'Qt5XmlPatterns',
    'Qt5Help',
    'Qt5Test',
    'Qt5Designer',
    'Qt5DBus',
    'Qt5Network',
    'Qt5OpenGL',
    'Qt5PrintSupport',
    'Qt5Svg',
    'Qt5WinExtras',
    'Qt5DataVisualization',
    'Qt5Chart',
    'Qt5TextToSpeech',
    'Qt53DCore',
    'Qt53DInput',
    'Qt53DLogic',
    'Qt53DRender',
    'Qt53DAnimation',
    'Qt53DExtras',
    'opengl32sw',
    'd3dcompiler',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('icon.ico', '.'), ('gear_icon.png', '.')],
    hiddenimports=['pytesseract', 'PIL', 'PIL.Image', 'PIL.ImageFilter', 'PIL.ImageEnhance'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_imports,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Filter out unused Qt5 DLLs
def filter_binaries(pyinstaller_binaries):
    filtered = []
    for name, path, typ in pyinstaller_binaries:
        skip = False
        for ex in excluded_binaries:
            if ex.lower() in name.lower():
                skip = True
                break
        if not skip:
            filtered.append((name, path, typ))
    return filtered

a.binaries = filter_binaries(a.binaries)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='POD Renamer - J&T Express (NM Rantau)',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)
