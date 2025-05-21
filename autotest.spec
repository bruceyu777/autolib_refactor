# -*- mode: python ; coding: utf-8 -*-


block_cipher = None

import os
import re
import subprocess
import time


def tree_datas(source, dest_prefix):
    """
    Recursively collects all files from the source directory,
    preserving their relative paths under dest_prefix.
    Returns a list of tuples in the format (source_file, destination_folder).
    """
    data_files = []
    for root, dirs, files in os.walk(source):
        for file in files:
            file_src = os.path.join(root, file)
            # Calculate the destination folder: remove the source prefix and join with dest_prefix
            relative_path = os.path.relpath(root, source)
            dest_folder = os.path.join(dest_prefix, relative_path)
            data_files.append((file_src, dest_folder))
    return data_files


def get_linux_version():
    try:
        result = subprocess.run(
            ["cat", "/etc/lsb-release"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        print("*" * 70)
        print(result.stdout)
        print("*" * 70)
        if result.returncode == 0:
            matched = re.search(r'DISTRIB_RELEASE=([\d.]+)', result.stdout)
            if matched:
                version = matched.group(1)
                return version.replace(".", "")
    except Exception as e:
        print(f"Error detecting Linux version: {e}")
    return ""


a = Analysis(
    ['autotest.py'],
    pathex=['lib'],
    binaries=[],
    datas=[
        ("version", "."),
        ("lib/services/fos/static/pltrev.csv", "lib/services/fos/static/"),
        ("lib/core/compiler/static/cli_syntax.json", "lib/core/compiler/static/"),
    ] + tree_datas("lib/services/static", "lib/services/static") + tree_datas("lib/core/device/ems/metadata/", "lib/core/device/ems/metadata"),
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


linux_version = get_linux_version()
version_suffix = f"_{linux_version}" if linux_version else ""

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=f'autotest{version_suffix}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    onefile=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None
)
