#!/usr/bin/env python3
"""
Archive Extraction Tool

Supports: .zip, .tar, .tar.gz, .tgz, .tar.bz2, .tbz2, .tar.xz, .7z, .rar

Usage:
    python extract_archive.py <archive_path> [extract_to]
    
    archive_path: Path to the archive file
    extract_to: Optional destination directory (defaults to archive's parent directory)

Examples:
    python extract_archive.py /path/to/file.zip
    python extract_archive.py /path/to/file.tar.gz /custom/output/dir
    python extract_archive.py file.7z
"""

import sys
import os
import zipfile
import tarfile
import shutil
from pathlib import Path


def extract_zip(archive_path, extract_to):
    """Extract ZIP archive."""
    print(f"Extracting ZIP archive: {archive_path}")
    with zipfile.ZipFile(archive_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    return True


def extract_tar(archive_path, extract_to, mode='r'):
    """Extract TAR archive (including .tar.gz, .tar.bz2, .tar.xz)."""
    print(f"Extracting TAR archive: {archive_path}")
    with tarfile.open(archive_path, mode) as tar_ref:
        tar_ref.extractall(extract_to)
    return True


def extract_7z(archive_path, extract_to):
    """Extract 7Z archive using py7zr."""
    try:
        import py7zr
    except ImportError:
        print("ERROR: py7zr library not installed.")
        print("Install it with: pip install py7zr")
        return False
    
    print(f"Extracting 7Z archive: {archive_path}")
    with py7zr.SevenZipFile(archive_path, mode='r') as z:
        z.extractall(path=extract_to)
    return True


def extract_rar(archive_path, extract_to):
    """Extract RAR archive using rarfile."""
    try:
        import rarfile
    except ImportError:
        print("ERROR: rarfile library not installed.")
        print("Install it with: pip install rarfile")
        print("Note: Also requires unrar command-line tool to be installed")
        return False
    
    print(f"Extracting RAR archive: {archive_path}")
    with rarfile.RarFile(archive_path) as rar_ref:
        rar_ref.extractall(extract_to)
    return True


def detect_archive_type(filepath):
    """Detect archive type based on file extension."""
    filepath_lower = filepath.lower()
    
    if filepath_lower.endswith('.zip'):
        return 'zip'
    elif filepath_lower.endswith('.7z'):
        return '7z'
    elif filepath_lower.endswith('.rar'):
        return 'rar'
    elif filepath_lower.endswith(('.tar.gz', '.tgz')):
        return 'tar.gz'
    elif filepath_lower.endswith(('.tar.bz2', '.tbz2', '.tb2')):
        return 'tar.bz2'
    elif filepath_lower.endswith(('.tar.xz', '.txz')):
        return 'tar.xz'
    elif filepath_lower.endswith('.tar'):
        return 'tar'
    else:
        return None


def extract_archive(archive_path, extract_to=None):
    """
    Extract archive to specified directory.
    
    Args:
        archive_path: Path to archive file
        extract_to: Optional extraction directory (defaults to archive's parent dir)
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Convert to absolute path
    archive_path = os.path.abspath(archive_path)
    
    # Check if archive exists
    if not os.path.isfile(archive_path):
        print(f"ERROR: Archive file not found: {archive_path}")
        return False
    
    # Determine extraction directory
    if extract_to is None:
        extract_to = os.path.dirname(archive_path)
    else:
        extract_to = os.path.abspath(extract_to)
    
    # Create extraction directory if it doesn't exist
    os.makedirs(extract_to, exist_ok=True)
    
    # Detect archive type
    archive_type = detect_archive_type(archive_path)
    
    if archive_type is None:
        print(f"ERROR: Unsupported archive format: {archive_path}")
        print("Supported formats: .zip, .tar, .tar.gz, .tgz, .tar.bz2, .tbz2, .tar.xz, .7z, .rar")
        return False
    
    print(f"Archive: {archive_path}")
    print(f"Extract to: {extract_to}")
    print(f"Type: {archive_type}")
    print("-" * 60)
    
    try:
        # Extract based on type
        if archive_type == 'zip':
            success = extract_zip(archive_path, extract_to)
        elif archive_type == '7z':
            success = extract_7z(archive_path, extract_to)
        elif archive_type == 'rar':
            success = extract_rar(archive_path, extract_to)
        elif archive_type == 'tar':
            success = extract_tar(archive_path, extract_to, 'r')
        elif archive_type == 'tar.gz':
            success = extract_tar(archive_path, extract_to, 'r:gz')
        elif archive_type == 'tar.bz2':
            success = extract_tar(archive_path, extract_to, 'r:bz2')
        elif archive_type == 'tar.xz':
            success = extract_tar(archive_path, extract_to, 'r:xz')
        else:
            print(f"ERROR: Unhandled archive type: {archive_type}")
            return False
        
        if success:
            print("-" * 60)
            print(f"✓ Successfully extracted to: {extract_to}")
            
            # Show extracted contents
            extracted_items = os.listdir(extract_to)
            if extracted_items:
                print(f"\nExtracted {len(extracted_items)} item(s):")
                for item in sorted(extracted_items)[:10]:  # Show first 10 items
                    print(f"  - {item}")
                if len(extracted_items) > 10:
                    print(f"  ... and {len(extracted_items) - 10} more")
            
            return True
        else:
            return False
            
    except Exception as e:
        print(f"ERROR: Failed to extract archive: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    archive_path = sys.argv[1]
    extract_to = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = extract_archive(archive_path, extract_to)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
