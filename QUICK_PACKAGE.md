# Quick Start: Packaging ScreenTranslate

## For Quick Sharing (Simplest)

**Step 1: Verify everything is ready**
```powershell
cd g:\NODEJS\ScreenTranslate
.\verify.bat
```

**Step 2: Create a ZIP archive**
```powershell
Compress-Archive -Path "g:\NODEJS\ScreenTranslate" -DestinationPath "g:\ScreenTranslate.zip" -Force
```

**Step 3: Share the ZIP file**
- Send `ScreenTranslate.zip` to target users
- Recipients extract it
- Recipients run `setup.bat`
- Recipients run `run.bat` to start the app

---

## Files Created for Packaging

| File | Purpose | Usage |
|------|---------|-------|
| **setup.bat** | One-click installer launcher | Double-click on target computer |
| **installer.ps1** | Main installation script (PowerShell) | Runs automatically via setup.bat |
| **run.bat** | Application launcher | Double-click to start ScreenTranslate |
| **build.py** | PyInstaller build script | `python build.py` to create standalone EXE |
| **verify.bat** | Package verification | Check if all files are present |
| **version.py** | App metadata and version info | Used by build scripts, contains app info |
| **PACKAGING.md** | Complete packaging documentation | Read for detailed distribution guides |

---

## Installation Flow (What setup.bat does)

```
setup.bat
  └─> installer.ps1 (PowerShell, admin mode)
       ├─ Check for Tesseract-OCR
       ├─ Create Python virtual environment
       ├─ Install dependencies from requirements.txt
       ├─ Verify tessdata OCR language files
       ├─ Create Windows Start Menu shortcut
       └─ Set environment variables
```

---

## What get users receive

### Method 1: ZIP Archive (~5 MB)
```
ScreenTranslate.zip
└─ ScreenTranslate/
    ├── screen_overlay_translator.py
    ├── requirements.txt
    ├── tessdata/ (OCR language data)
    ├── setup.bat
    ├── run.bat
    ├── installer.ps1
    ├── README.md
    └── README.vi.md
```

**Requires:** Python 3.8+, Windows

### Method 2: Standalone (~150 MB)
```
ScreenTranslate_Standalone.zip
└─ ScreenTranslate/
    ├── ScreenTranslate.exe (self-contained)
    ├── _internal/ (bundled libraries)
    ├── tessdata/ (OCR language data)
    ├── run.bat
    └── README.md
```

**Requires:** Windows only, no Python needed

---

## Common Tasks

### Create a ZIP for distribution
```powershell
cd g:\NODEJS\ScreenTranslate
Compress-Archive -Path . -DestinationPath ../ScreenTranslate.zip -Force
```

### Build standalone EXE version
```powershell
pip install pyinstaller
cd g:\NODEJS\ScreenTranslate
python build.py
# Creates dist/ScreenTranslate/ScreenTranslate.exe
```

### Test installation on same machine
```powershell
cd g:\NODEJS\ScreenTranslate
cmd /k setup.bat
```

### Check if package is ready
```powershell
cd g:\NODEJS\ScreenTranslate
.\verify.bat
```

---

## What Installer Does

1. **Tesseract Check**
   - Detects if Tesseract-OCR is installed
   - Prompts user to download if missing
   - Sets SCREEN_TRANSLATE_TESSERACT_CMD environment variable

2. **Python Environment**
   - Creates `.venv` virtual environment in project folder
   - Installs all dependencies from `requirements.txt`

3. **Language Data**
   - Verifies `tessdata/` folder with 5 language files:
     - eng.traineddata (English)
     - chi_sim.traineddata (Chinese)
     - jpn.traineddata (Japanese)
     - kor.traineddata (Korean)
     - vie.traineddata (Vietnamese)

4. **Shortcuts**
   - Creates Windows Start Menu shortcut
   - LaunchPath: `run.bat`
   - Working directory: project folder

5. **Environment Variables**
   - Sets SCREEN_TRANSLATE_TESSERACT_CMD if Tesseract found
   - Sets TESSDATA_PREFIX to tessdata folder

---

## Testing Fresh Installation

1. Extract ScreenTranslate.zip to test folder
2. Run `setup.bat`
3. Wait for installation to complete
4. Run `run.bat` or click Start Menu shortcut
5. Press Ctrl+Shift+E to test OCR functionality

---

## Troubleshooting

### "PowerShell execution policy" error
**Fix:** Run as Administrator or use:
```powershell
powershell -ExecutionPolicy Bypass -File installer.ps1
```

### "Tesseract not found" error
**Fix:** Download from https://github.com/UB-Mannheim/tesseract/releases

### "ModuleNotFoundError" error
**Fix:** Ensure `setup.bat` ran successfully and dependencies installed

### Old version running
**Fix:** Make sure `run.bat` uses the correct `.venv` Python executable

---

## Next Steps

1. **Run verify.bat to check package completeness**
   ```powershell
   .\verify.bat
   ```

2. **Create distribution ZIP**
   ```powershell
   Compress-Archive -Path . -DestinationPath ../ScreenTranslate.zip -Force
   ```

3. **Share the ZIP with users**
   - They extract it
   - They run setup.bat
   - They run run.bat or click Start Menu shortcut

4. **(Optional) Create standalone EXE**
   ```powershell
   pip install pyinstaller
   python build.py
   ```

---

## See Also

- **PACKAGING.md** - Comprehensive packaging guide with all methods
- **README.md** - User documentation (English)
- **README.vi.md** - User documentation (Vietnamese)
