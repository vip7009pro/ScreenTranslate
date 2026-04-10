#!/usr/bin/env python3
"""
Version and packaging information for ScreenTranslate
This file is used by build.py and installation scripts
"""

__version__ = "1.0.0"
__author__ = "ScreenTranslate Contributors"
__description__ = "Windows Desktop Screen Overlay Translator with OCR and Multi-language Support"

# Application metadata
APP_NAME = "ScreenTranslate"
APP_VERSION = __version__
PYTHON_REQUIRED = "3.8"

# Supported languages
SUPPORTED_LANGUAGES = {
    "en": "English",
    "zh": "Chinese (Simplified)",
    "ja": "日本語",
    "ko": "한국어",
    "vi": "Tiếng Việt",
}

# OCR languages with training data
OCR_SUPPORTED_LANGUAGES = ["eng", "chi_sim", "jpn", "kor", "vie"]

# Dependencies
DEPENDENCIES = [
    "PyQt6>=6.6",
    "pytesseract>=0.3.13",
    "mss>=9.0.1",
    "Pillow>=10.0.0",
    "deep-translator>=1.11.4",
    "keyboard>=0.13.5",
]

# Build requirements (for PyInstaller)
BUILD_DEPENDENCIES = [
    "PyInstaller>=5.0",
]

if __name__ == "__main__":
    print(f"{APP_NAME} v{APP_VERSION}")
    print(f"Python {PYTHON_REQUIRED}+ required")
    print(f"Supported languages: {', '.join(SUPPORTED_LANGUAGES.values())}")
