# ScreenTranslate Packaging Guide

## Overview

This guide explains how to package ScreenTranslate into a standalone application that can be installed and run on other computers.

## Packaging Methods

### Method 1: Simple Batch Installation (Recommended for quick distribution)

The simplest way to distribute ScreenTranslate is to share the entire project folder with these scripts:

**Files included:**
- `screen_overlay_translator.py` - Main application
- `requirements.txt` - Python dependencies
- `tessdata/` - OCR language data
- `setup.bat` - One-click installer
- `run.bat` - Application launcher
- `README.md` & `README.vi.md` - Documentation

**Distribution steps:**

1. **Compress the project folder:**
   ```powershell
   # Create a ZIP archive with all files
   Compress-Archive -Path "g:\NODEJS\ScreenTranslate" -DestinationPath "ScreenTranslate.zip" -Force
   ```

2. **Send `ScreenTranslate.zip` to target computer**

3. **On target computer:**
   - Extract the ZIP file
   - Double-click `setup.bat`
   - Follow the installation wizard
   - Launch from Start Menu shortcut or `run.bat`

**Advantages:**
- ✅ No conversion, just compress and share
- ✅ Users can update files easily
- ✅ Small archive size
- ✅ All language data included

**Disadvantages:**
- ⚠️ Requires Python 3.8+ on target computer
- ⚠️ First run takes time for pip to install dependencies

---

### Method 2: PyInstaller Standalone EXE (Best for non-technical users)

Create a standalone `.exe` file with all dependencies bundled.

**Prerequisites:**
```powershell
pip install pyinstaller
```

**Build steps:**

1. **Run the build script:**
   ```powershell
   cd g:\NODEJS\ScreenTranslate
   python build.py
   ```

2. **Wait for build to complete (3-5 minutes)**
   - This creates `dist/ScreenTranslate/ScreenTranslate.exe`
   - Includes all Python libraries bundled in the .exe

3. **Package the executable:**
   ```powershell
   # Create distribution folder
   mkdir ScreenTranslate_Portable
   copy "dist\ScreenTranslate\*" "ScreenTranslate_Portable\"
   copy "tessdata\*" "ScreenTranslate_Portable\tessdata\"
   copy "run.bat" "ScreenTranslate_Portable\"
   copy "README.md" "ScreenTranslate_Portable\"
   
   # Create ZIP
   Compress-Archive -Path "ScreenTranslate_Portable" -DestinationPath "ScreenTranslate_Portable.zip" -Force
   ```

4. **Distribution on target computer:**
   - Extract `ScreenTranslate_Portable.zip`
   - Double-click `run.bat` to launch
   - OR double-click `ScreenTranslate.exe` directly

**Advantages:**
- ✅ No Python installation needed
- ✅ Works on any Windows system
- ✅ Faster first launch
- ✅ Can run from anywhere

**Disadvantages:**
- ⚠️ Larger file size (~100-150 MB)
- ⚠️ Still requires Tesseract-OCR installed separately
- ⚠️ Longer initial build time

---

### Method 3: Full Installer with Tesseract (Professional deployment)

Create a complete installer that includes Tesseract.

**Prerequisites:**
- InnoSetup (optional, for professional installer)
- OR use batch/PowerShell scripts directly

**Package contents:**
```
ScreenTranslate_Installer/
├── ScreenTranslate.exe (from PyInstaller)
├── tessdata/
├── setup.bat
├── installer.ps1
├── install_tesseract.ps1
└── README.md
```

**Build and distribution:**

1. Build executable with PyInstaller (Method 2)
2. Run installer on target: `setup.bat`
3. Installer automatically:
   - Checks for Tesseract, prompts to install if missing
   - Sets up Python environment
   - Configures environment variables
   - Creates Start Menu shortcuts

---

## Installation Scripts Explained

### `setup.bat`
- Launches the PowerShell installer
- Requires Windows only (no additional tools)
- Call with: `setup.bat`

### `installer.ps1`
- **Main installation script**
- Requires Admin privileges (auto-elevates)
- Functions:
  - Detects Tesseract installation
  - Creates Python virtual environment
  - Installs dependencies from `requirements.txt`
  - Verifies OCR language data in `tessdata/`
  - Creates Windows Start Menu shortcut
  - Sets up environment variables

**Manual run (elevated PowerShell):**
```powershell
powershell -ExecutionPolicy Bypass -File c:\path\to\installer.ps1
```

### `run.bat`
- **Application launcher**
- Activates virtual environment
- Sets TESSDATA_PREFIX environment variable
- Launches `screen_overlay_translator.py`
- Call with: `run.bat`

---

## Build Script Explained

### `build.py`
- Uses PyInstaller to convert Python to executable
- Bundles all Python dependencies
- Includes `tessdata/` folder in binary
- Includes README files

**Run with:**
```powershell
cd g:\NODEJS\ScreenTranslate
python build.py
```

**Output:**
- `dist/ScreenTranslate/ScreenTranslate.exe` - Main executable
- `build/` - Build artifacts
- `ScreenTranslate.spec` - PyInstaller specification

---

## Quick Start (Recommended for sharing)

### For recipients with Python installed (Method 1):

1. **Sender:**
   ```powershell
   Compress-Archive -Path "g:\NODEJS\ScreenTranslate" -DestinationPath "ScreenTranslate.zip"
   # Share ScreenTranslate.zip
   ```

2. **Recipient:**
   - Extract ZIP
   - Run `setup.bat`
   - Run `run.bat` after installation

### For recipients without Python (Method 2):

1. **Sender:**
   ```powershell
   python build.py
   # Share dist/ScreenTranslate folder
   ```

2. **Recipient:**
   - Copy folder to computer
   - Run `run.bat`

---

## Environment Variables

The application uses these environment variables (optional, auto-detected):

```
SCREEN_TRANSLATE_TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
TESSDATA_PREFIX=C:\path\to\tessdata
```

Setting these is usually NOT needed—the app auto-detects:
- ✅ Auto-finds Tesseract in `Program Files`
- ✅ Auto-finds tessdata in application folder

---

## Troubleshooting

### Issue: "Tesseract not found"
**Solution:** Install from https://github.com/UB-Mannheim/tesseract/releases

### Issue: "ModuleNotFoundError: No module named 'PyQt6'"
**Solution:** Run `setup.bat` to install dependencies

### Issue: "tessdata directory not found"
**Solution:** Ensure `tessdata/` folder is in the same directory as the executable

### Issue: Build fails with "PyInstaller not installed"
**Solution:**
```powershell
pip install pyinstaller
python build.py
```

### Issue: Permission denied when running installer
**Solution:** Right-click `setup.bat` → "Run as administrator"

---

## Full Workflow Example

### Create and distribute complete package:

```powershell
# Navigate to project
cd g:\NODEJS\ScreenTranslate

# Option A: Simple ZIP distribution (Method 1)
Compress-Archive -Path . -DestinationPath ..\ScreenTranslate.zip -Force
# Share "../ScreenTranslate.zip" - Recipients extract and run setup.bat

# Option B: Standalone EXE (Method 2)
python build.py
# Create dist folder and compress
Compress-Archive -Path "dist\ScreenTranslate" -DestinationPath ..\ScreenTranslate_Standalone.zip -Force
# Share "../ScreenTranslate_Standalone.zip" - Just extract and run .exe
```

---

## File Structure for Distribution

### Method 1 Structure:
```
ScreenTranslate/
├── screen_overlay_translator.py
├── requirements.txt
├── tessdata/
│   ├── eng.traineddata
│   ├── chi_sim.traineddata
│   ├── jpn.traineddata
│   ├── kor.traineddata
│   └── vie.traineddata
├── setup.bat
├── run.bat
├── installer.ps1
├── README.md
└── README.vi.md
```

### Method 2 Structure:
```
ScreenTranslate_Standalone/
├── ScreenTranslate.exe
├── _internal/  (bundled libraries)
├── tessdata/
├── run.bat
└── README.md
```

---

## Summary

| Method | Size | Setup Time | Python Required | Best For |
|--------|------|-----------|-----------------|----------|
| **Method 1: ZIP** | ~5 MB | 5-10 min | Yes | Quick distribution to Python users |
| **Method 2: Standalone** | ~150 MB | 2-3 min | No | Non-technical users, portable |
| **Method 3: Installer** | ~200 MB | 3-5 min | No | Professional deployment, all-in-one |

**Recommended for most users: Method 1** - Fastest to package, smallest file, works on all systems with Python.

**Recommended for non-technical users: Method 2** - No Python needed, just extract and run.
