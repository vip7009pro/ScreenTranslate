"""
PyInstaller build script for ScreenTranslate
Creates a standalone .exe executable with bundled dependencies
"""

import os
import sys
import subprocess
from pathlib import Path

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.absolute()

# PyInstaller specifications
SPEC_CONTENT = f'''
# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

a = Analysis(
    [r'{PROJECT_ROOT}\\screen_overlay_translator.py'],
    pathex=[r'{PROJECT_ROOT}'],
    binaries=[],
    datas=[
        (r'{PROJECT_ROOT}\\tessdata', 'tessdata'),
        (r'{PROJECT_ROOT}\\README.md', '.'),
        (r'{PROJECT_ROOT}\\README.vi.md', '.'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'pytesseract',
        'mss',
        'PIL',
        'deep_translator',
        'keyboard',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludedimports=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ScreenTranslate',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
'''

def build_executable():
    """Build the PyInstaller executable"""
    print("=" * 60)
    print("ScreenTranslate PyInstaller Build")
    print("=" * 60)
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("\n❌ Error: PyInstaller not installed")
        print("Install it with: pip install pyinstaller")
        sys.exit(1)
    
    # Write spec file
    spec_file = PROJECT_ROOT / "ScreenTranslate.spec"
    print(f"\n📝 Creating spec file: {spec_file}")
    with open(spec_file, 'w') as f:
        f.write(SPEC_CONTENT)
    
    # Run PyInstaller
    print(f"\n🔨 Building executable...")
    build_cmd = [
        sys.executable,
        "-m", "PyInstaller",
        str(spec_file),
        "--distpath", str(PROJECT_ROOT / "dist"),
        "--buildpath", str(PROJECT_ROOT / "build"),
        "--specpath", str(PROJECT_ROOT),
    ]
    
    result = subprocess.run(build_cmd, cwd=str(PROJECT_ROOT))
    
    if result.returncode == 0:
        print("\n✅ Build successful!")
        exe_path = PROJECT_ROOT / "dist" / "ScreenTranslate" / "ScreenTranslate.exe"
        print(f"\n📦 Executable created at: {exe_path}")
        print(f"\n📋 Next steps:")
        print(f"   1. Run the installer: powershell -ExecutionPolicy Bypass -File installer.ps1")
        print(f"   2. Or distribute the 'dist/ScreenTranslate' folder to other computers")
        print(f"   3. Run setup.bat on target computer to install dependencies")
    else:
        print(f"\n❌ Build failed with code {result.returncode}")
        sys.exit(1)

if __name__ == "__main__":
    os.chdir(str(PROJECT_ROOT))
    build_executable()
