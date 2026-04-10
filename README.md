# Screen Overlay Translator

Screen Overlay Translator is a Windows desktop app that behaves like the Android "Screen Translate" feature.
It lets you snip a region of the screen, run OCR on the captured image, translate the detected text, and paint the translated result back on top of the selected area in a transparent overlay.

## Highlights

- System tray app with a global hotkey.
- Transparent full-screen snipping overlay.
- DPI-aware capture pipeline so the selected region matches the monitor coordinates.
- OCR powered by Tesseract via `pytesseract`.
- Translation via `deep-translator` using Google Translate.
- Transparent always-on-top result overlay.
- Copy all translated text or copy only the selected text block.
- Runtime switching of source OCR language and target translation language.
- Built-in support files for English, Chinese Simplified, Japanese, Korean, and Vietnamese OCR.

## Supported Languages

The app currently supports these language choices in the tray menu:

- Auto detect
- English
- Chinese (Simplified)
- Japanese
- Korean
- Vietnamese

Default target language: Vietnamese.

## End-to-End Pipeline

The app follows this pipeline every time you trigger a translation session:

```text
Hotkey pressed
  -> system tray hotkey service
  -> transparent snipping overlay opens
  -> user drags a rectangle
  -> selected rectangle is captured with DPI-aware screen mapping
  -> image is passed to Tesseract OCR
  -> OCR words are filtered by confidence
  -> words are grouped into blocks/lines
  -> each block is translated
  -> transparent overlay is created at the same screen position
  -> translated labels are painted over the original text area
  -> user can copy all text or only the selected block
```

### Step 1: Hotkey and tray service

The app stays in the system tray and listens for `Ctrl+Shift+E`.
On Windows, the hotkey is registered with native `RegisterHotKey` for stability.
If the native registration cannot be created, the app falls back to the `keyboard` package.

### Step 2: Snipping mode

When you press the hotkey, the app shows a semi-transparent full-screen overlay.
You drag with the mouse to define the capture rectangle.
The overlay closes immediately after the selection is made.

### Step 3: Screen capture

The selected rectangle is captured with `mss`.
The app maps Qt logical coordinates to physical screen coordinates using the current monitor DPI scale.
That is what keeps the capture aligned with the overlay on scaled Windows displays.

### Step 4: OCR

The captured image is sent to Tesseract with `pytesseract.image_to_data()`.
The app extracts:

- text
- left / top / width / height
- confidence
- line and block grouping metadata

Low-confidence noise and empty strings are removed.
Words are grouped into logical text blocks so translation keeps context instead of translating each word in isolation.

### Step 5: Translation

Each OCR block is translated with `deep-translator`.
The source OCR language and target translation language are chosen from the tray menu.
The target defaults to Vietnamese.

### Step 6: Result overlay

A new frameless, transparent, always-on-top PyQt window is created at the same on-screen position as the captured region.
For each translated block, the app creates a label and places it at the OCR coordinates.
The label background is solid enough to hide the original text under it.

The overlay also includes:

- `All` button: copy all translated text to the clipboard
- `Sel` button: copy only the currently selected translated block
- `X` button: close the overlay

Click a translated block to select it before using `Sel`.

## Installation

### 1. Install Python dependencies

Use the project virtual environment and install the required packages:

```powershell
python -m pip install -r requirements.txt
```

If you are using the workspace venv directly, you can also run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Install Tesseract-OCR for Windows

Install Tesseract for Windows, for example the UB Mannheim build.

After installation, make sure `tesseract.exe` is available on PATH, or set this environment variable:

```powershell
$env:SCREEN_TRANSLATE_TESSERACT_CMD = 'C:\Program Files\Tesseract-OCR'
```

You can point it either to the install folder or directly to `tesseract.exe`.
The app will auto-resolve both.

### 3. Verify OCR language data

This repository includes a local `tessdata` folder with these traineddata files:

- `eng.traineddata`
- `chi_sim.traineddata`
- `jpn.traineddata`
- `kor.traineddata`
- `vie.traineddata`

When the local `tessdata` folder is present, the app uses it automatically.
That makes the supported language set work without depending on the system Tesseract installation.

## Running the App

From the project root:

```powershell
.\.venv\Scripts\python.exe .\screen_overlay_translator.py
```

Once the tray icon appears:

1. Press `Ctrl+Shift+E`.
2. Drag to select the screen area you want to translate.
3. Wait for OCR and translation.
4. Use the overlay buttons to copy text or close the overlay.

## Changing Source and Target Languages

Open the tray icon menu and use:

- `Source OCR language`
- `Target translation language`

The source language affects OCR.
The target language affects translation output.

The available choices are the same supported languages listed above.
Target language defaults to Vietnamese.

## Copying Text

The translation overlay provides two copy actions:

- `All` copies every translated block in reading order.
- `Sel` copies only the block you clicked last.

This is useful when the overlay contains multiple translated regions and you only need one sentence or paragraph.

## Configuration

The main environment variable you may want to set is:

- `SCREEN_TRANSLATE_TESSERACT_CMD`: path to `tesseract.exe` or the Tesseract install folder

The app also supports `SCREEN_TRANSLATE_OCR_CONFIG` if you want to change the OCR engine flags.
The default config is tuned for screen text and is usually the best place to start.

## Project Structure

- `screen_overlay_translator.py` - main application entry point and all GUI/OCR/translation logic
- `requirements.txt` - Python dependencies
- `tessdata/` - local OCR language data used by Tesseract
- `CONTEXT.md` - workspace notes and current implementation status

## Troubleshooting

### Tesseract is not found

If the app says Tesseract is not installed or not in PATH, check these first:

1. Confirm `tesseract.exe` exists.
2. Make sure `SCREEN_TRANSLATE_TESSERACT_CMD` points to the install folder or the executable itself.
3. Confirm the local workspace venv can run `pytesseract.get_tesseract_version()`.

### Korean, Japanese, or Chinese text is not detected

If a language does not recognize correctly:

1. Make sure the matching `.traineddata` file exists in `tessdata/`.
2. Switch the source OCR language in the tray menu.
3. Verify the local `tessdata` folder is still present next to `screen_overlay_translator.py`.

### Translation output looks wrong

Translation is handled by Google Translate through `deep-translator`.
If translation fails, check network connectivity and try again.

### Copy buttons do nothing

Make sure the overlay is focused and that at least one translated block is present.
Click a block first, then use `Sel`.

## Notes

- This is a Windows-only implementation.
- The app is designed to work with monitor scaling and multiple displays.
- The code paths for OCR and overlay positioning are intentionally kept separate so the capture geometry stays precise.
