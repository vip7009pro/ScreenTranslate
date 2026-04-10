# PowerShell Installer for ScreenTranslate
# Run with: powershell -ExecutionPolicy Bypass -File installer.ps1

param(
    [switch]$AdminCheck = $true,
    [switch]$SkipTesseract = $false,
    [switch]$SkipPython = $false
)

# Colors for output
function Write-Info { Write-Host "ℹ️  $args" -ForegroundColor Cyan }
function Write-Success { Write-Host "✅ $args" -ForegroundColor Green }
function Write-Error_ { Write-Host "❌ $args" -ForegroundColor Red }
function Write-Warning_ { Write-Host "⚠️  $args" -ForegroundColor Yellow }

Write-Host "`n" + "=" * 70
Write-Host "ScreenTranslate Installer" -ForegroundColor Cyan
Write-Host "=" * 70 + "`n"

# Check admin rights
if ($AdminCheck) {
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
    if (-not $isAdmin) {
        Write-Warning_ "This script requires administrator privileges"
        Write-Info "Restarting with elevated privileges..."
        Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" -AdminCheck:`$false" -Verb RunAs
        exit
    }
}

# Get script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommandPath
$installDir = $scriptDir

Write-Info "Installation directory: $installDir"

# Step 1: Install Tesseract if needed
if (-not $SkipTesseract) {
    Write-Host "`n--- Step 1: Tesseract-OCR ---`n"
    
    $tesseractPaths = @(
        "C:\Program Files\Tesseract-OCR\tesseract.exe",
        "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        "${env:ProgramFiles}\Tesseract-OCR\tesseract.exe",
        "${env:ProgramFiles(x86)}\Tesseract-OCR\tesseract.exe"
    )
    
    $tesseractFound = $false
    foreach ($path in $tesseractPaths) {
        if (Test-Path $path) {
            Write-Success "Tesseract-OCR found at: $path"
            $tesseractFound = $true
            break
        }
    }
    
    if (-not $tesseractFound) {
        Write-Warning_ "Tesseract-OCR not found"
        Write-Info "Downloading Tesseract-OCR installer..."
        
        $tesseractUrl = "https://github.com/UB-Mannheim/tesseract/wiki"
        Write-Info "Please download Tesseract from: https://github.com/UB-Mannheim/tesseract/releases"
        Write-Info "Recommended: tesseract-ocr-w64-setup-v5.x.exe"
        Write-Info "Install to default location: C:\Program Files\Tesseract-OCR"
        
        Write-Host "`nPress any key after Tesseract installation completes..."
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    } else {
        Write-Success "Tesseract-OCR is already installed"
    }
}

# Step 2: Create/Update Python virtual environment
Write-Host "`n--- Step 2: Python Virtual Environment ---`n"

$venvPath = Join-Path $installDir ".venv"

if (Test-Path $venvPath) {
    Write-Info "Virtual environment found at: $venvPath"
} else {
    Write-Info "Creating Python virtual environment..."
    if (-not $SkipPython) {
        try {
            python -m venv $venvPath
            Write-Success "Virtual environment created"
        }
        catch {
            Write-Error_ "Failed to create virtual environment"
            Write-Error_ "Make sure Python 3.8+ is installed and in PATH"
            exit 1
        }
    }
}

# Step 3: Install Python dependencies
Write-Host "`n--- Step 3: Python Dependencies ---`n"

$pythonExe = Join-Path $venvPath "Scripts\python.exe"
$pipExe = Join-Path $venvPath "Scripts\pip.exe"

if (-not $SkipPython) {
    Write-Info "Installing Python packages from requirements.txt..."
    
    $requirementsFile = Join-Path $installDir "requirements.txt"
    if (Test-Path $requirementsFile) {
        try {
            & $pythonExe -m pip install --upgrade pip
            & $pythonExe -m pip install -r $requirementsFile
            Write-Success "Python dependencies installed"
        }
        catch {
            Write-Error_ "Failed to install Python dependencies"
            Write-Info "Try running manually: $pipExe install -r $requirementsFile"
        }
    } else {
        Write-Error_ "requirements.txt not found at: $requirementsFile"
    }
}

# Step 4: Verify tessdata
Write-Host "`n--- Step 4: Verify OCR Language Data ---`n"

$tessdataPath = Join-Path $installDir "tessdata"
if (Test-Path $tessdataPath) {
    $trainedDataFiles = Get-ChildItem -Path $tessdataPath -Filter "*.traineddata" | Measure-Object
    if ($trainedDataFiles.Count -gt 0) {
        Write-Success "OCR language data found: $($trainedDataFiles.Count) traineddata files"
        Get-ChildItem -Path $tessdataPath -Filter "*.traineddata" | ForEach-Object {
            Write-Info "  - $($_.Name)"
        }
    } else {
        Write-Warning_ "No traineddata files found in tessdata directory"
    }
} else {
    Write-Warning_ "tessdata directory not found"
}

# Step 5: Create shortcuts
Write-Host "`n--- Step 5: Create Shortcuts ---`n"

$shortcutDir = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs"
$shortcutPath = Join-Path $shortcutDir "ScreenTranslate.lnk"

$pythonScript = Join-Path $installDir "screen_overlay_translator.py"
$runBatPath = Join-Path $installDir "run.bat"

Write-Info "Creating start menu shortcut..."

# Create the shell.CreateObject for shortcut
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $runBatPath
$shortcut.WorkingDirectory = $installDir
$shortcut.IconLocation = $pythonExe
$shortcut.Save()

Write-Success "Shortcut created at: $shortcutPath"

# Step 6: Environment variables
Write-Host "`n--- Step 6: Environment Variables ---`n"

$tesseractExe = $null
foreach ($path in $tesseractPaths) {
    if (Test-Path $path) {
        $tesseractExe = $path
        break
    }
}

if ($tesseractExe) {
    Write-Info "Setting SCREEN_TRANSLATE_TESSERACT_CMD environment variable..."
    [Environment]::SetEnvironmentVariable("SCREEN_TRANSLATE_TESSERACT_CMD", $tesseractExe, "User")
    Write-Success "Environment variable set for current user"
}

# Step 7: Display summary
Write-Host "`n" + "=" * 70
Write-Host "Installation Summary" -ForegroundColor Cyan
Write-Host "=" * 70 + "`n"

Write-Success "Installation complete!"
Write-Host "`nℹ️  Installation Path: $installDir"
Write-Host "📄 Start Menu Shortcut: $shortcutPath"
Write-Host "▶️  To run: Execute $shortcutPath or double-click run.bat"
Write-Host "`n📋 What was installed:"
Write-Host "   • Python virtual environment (.venv)"
Write-Host "   • Python dependencies from requirements.txt"
Write-Host "   • Start menu shortcut"
Write-Host "   • Environment variables configured"

Write-Host "`n🎯 Next steps:"
Write-Host "   1. Launch ScreenTranslate from Start Menu or run.bat"
Write-Host "   2. Press Ctrl+Shift+E to start translating"
Write-Host "   3. Use the system tray menu to change languages"

Write-Host "`n📚 Documentation:"
Write-Host "   • English: README.md"
Write-Host "   • Vietnamese: README.vi.md"

Write-Host "`n" + "=" * 70
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
