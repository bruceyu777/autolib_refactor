# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['autotest.py'],
    pathex=['lib'],
    binaries=[],
    datas=[
        ("lib/services/fos/static/pltrev.csv", "./lib/services/fos/static/"),
        ("lib/core/compiler/static/cli_syntax.json", "./lib/core/compiler/static/"),
        ("lib/services/static/", "./lib/services/static/"),
        ("lib/core/device/ems/metadata", "./lib/core/device/ems/metadata"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AutoLib_v3',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None
)
