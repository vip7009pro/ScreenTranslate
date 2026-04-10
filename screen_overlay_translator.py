"""Screen Overlay Translator

Windows desktop app that captures a snipped region, performs OCR with
pytesseract, translates the text to the selected target language, and paints
the translation back onto a transparent always-on-top overlay.

Install steps:
1. Install the Python dependencies:
   pip install -r requirements.txt
2. Install Tesseract-OCR for Windows.
   The easiest build is the UB Mannheim installer.
3. If tesseract.exe is not on PATH, set SCREEN_TRANSLATE_TESSERACT_CMD to
    either the full path to tesseract.exe or the Tesseract-OCR install folder.
    The app will also auto-detect the standard Windows install location.
4. The tray menu lets you switch source OCR language and target translation
    language at runtime.
5. Supported languages: English, Chinese (Simplified), Japanese, Korean,
    and Vietnamese. Target defaults to Vietnamese.
6. The workspace includes `tessdata/eng.traineddata`, `chi_sim.traineddata`,
    `jpn.traineddata`, `kor.traineddata`, and `vie.traineddata` so OCR can use
    all supported languages.
7. Run the app:
   python screen_overlay_translator.py

Hotkey:
- Ctrl+Shift+E starts snipping mode.

Notes:
- The app is designed for Windows and uses a DPI-aware coordinate pipeline.
- Translation requires network access for Google Translate via deep-translator.
"""

from __future__ import annotations

import ctypes
import os
import shutil
import sys
import threading
from dataclasses import dataclass
from ctypes import wintypes
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TypedDict, cast

from PIL import Image
from deep_translator import GoogleTranslator
from mss import mss
from pytesseract import Output
import pytesseract

try:
    import keyboard
except Exception:  # pragma: no cover - import-time safety
    keyboard = None

from PyQt6.QtCore import QPoint, QRect, Qt, QSettings, pyqtSignal, QObject
from PyQt6.QtGui import QAction, QActionGroup, QBrush, QColor, QFont, QFontMetrics, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QMenu,
    QMessageBox,
    QPushButton,
    QLabel,
    QSystemTrayIcon,
    QWidget,
)


APP_NAME = "Screen Overlay Translator"
HOTKEY = "ctrl+shift+e"
HOTKEY_ID = 0xA11E
HOTKEY_MODIFIERS = 0x0002 | 0x0004
HOTKEY_VK = ord("E")
OCR_CONFIDENCE_THRESHOLD = float(os.environ.get("SCREEN_TRANSLATE_OCR_THRESHOLD", "40"))
OCR_CONFIG_BASE = os.environ.get("SCREEN_TRANSLATE_OCR_CONFIG", "--oem 3 --psm 6")
LOCAL_TESSDATA_DIR = Path(__file__).resolve().parent / "tessdata"
DEFAULT_SOURCE_LANGUAGE_KEY = "auto"
DEFAULT_TARGET_LANGUAGE_KEY = "vi"


@dataclass(frozen=True)
class LanguageChoice:
    key: str
    label: str
    ocr_codes: Tuple[str, ...]
    translation_code: str


@dataclass(frozen=True)
class TranslationProfile:
    source_key: str
    target_key: str
    source_label: str
    target_label: str
    ocr_lang: str
    ocr_config: str
    translation_source: str
    translation_target: str


LANGUAGE_CHOICES: Tuple[LanguageChoice, ...] = (
    LanguageChoice("auto", "Auto detect", ("eng", "chi_sim", "jpn", "kor", "vie"), "auto"),
    LanguageChoice("en", "English", ("eng",), "en"),
    LanguageChoice("zh", "Chinese (Simplified)", ("chi_sim",), "zh-CN"),
    LanguageChoice("ja", "Japanese", ("jpn",), "ja"),
    LanguageChoice("ko", "Korean", ("kor",), "ko"),
    LanguageChoice("vi", "Vietnamese", ("vie",), "vi"),
)
LANGUAGE_CHOICES_BY_KEY = {choice.key: choice for choice in LANGUAGE_CHOICES}
SOURCE_LANGUAGE_KEYS = tuple(choice.key for choice in LANGUAGE_CHOICES)
TARGET_LANGUAGE_KEYS = tuple(choice.key for choice in LANGUAGE_CHOICES if choice.key != "auto")


def language_choice_for_key(key: str) -> LanguageChoice:
    return LANGUAGE_CHOICES_BY_KEY.get(key, LANGUAGE_CHOICES_BY_KEY[DEFAULT_SOURCE_LANGUAGE_KEY])


def resolve_tesseract_executable() -> Optional[str]:
    candidates: List[str] = []

    env_value = os.environ.get("SCREEN_TRANSLATE_TESSERACT_CMD", "").strip()
    if env_value:
        env_path = Path(env_value)
        if env_path.is_file():
            candidates.append(str(env_path))
        elif env_path.is_dir():
            candidates.append(str(env_path / "tesseract.exe"))
        else:
            candidates.append(env_value)

    which_path = shutil.which("tesseract")
    if which_path:
        candidates.append(which_path)

    candidates.extend(
        [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
    )

    for candidate in candidates:
        try:
            if candidate and Path(candidate).is_file():
                return str(Path(candidate))
        except Exception:
            continue

    return None


def available_local_ocr_codes() -> set[str]:
    if not LOCAL_TESSDATA_DIR.is_dir():
        return set()
    return {path.stem for path in LOCAL_TESSDATA_DIR.glob("*.traineddata")}


def resolve_ocr_settings(source_key: str) -> Tuple[str, str]:
    choice = language_choice_for_key(source_key)
    selected_codes = list(choice.ocr_codes)
    local_codes = available_local_ocr_codes()

    if local_codes:
        selected_codes = [code for code in selected_codes if code in local_codes]

    if not selected_codes:
        try:
            installed_codes = set(pytesseract.get_languages(config=""))
        except Exception:
            installed_codes = set()
        selected_codes = [code for code in choice.ocr_codes if code in installed_codes]

    if not selected_codes:
        selected_codes = ["eng"]

    config = OCR_CONFIG_BASE
    if all((LOCAL_TESSDATA_DIR / f"{code}.traineddata").is_file() for code in selected_codes):
        config = f"{config} --tessdata-dir {LOCAL_TESSDATA_DIR.as_posix()}"

    return "+".join(selected_codes), config


def resolve_translation_code(language_key: str) -> str:
    return language_choice_for_key(language_key).translation_code


def build_translation_profile(source_key: str, target_key: str) -> TranslationProfile:
    source_choice = language_choice_for_key(source_key)
    target_choice = language_choice_for_key(target_key)
    ocr_lang, ocr_config = resolve_ocr_settings(source_choice.key)
    return TranslationProfile(
        source_key=source_choice.key,
        target_key=target_choice.key,
        source_label=source_choice.label,
        target_label=target_choice.label,
        ocr_lang=ocr_lang,
        ocr_config=ocr_config,
        translation_source=resolve_translation_code(source_choice.key),
        translation_target=resolve_translation_code(target_choice.key),
    )
@dataclass(frozen=True)
class ScreenInfo:
    device_name: str
    logical_geometry: QRect
    physical_geometry: QRect
    scale_x: float
    scale_y: float


@dataclass(frozen=True)
class WindowsMonitorInfo:
    device_name: str
    physical_geometry: QRect


@dataclass(frozen=True)
class TextBlock:
    left: int
    top: int
    width: int
    height: int
    original_text: str
    translated_text: str


class OCRWord(TypedDict):
    text: str
    left: int
    top: int
    width: int
    height: int
    line_num: int
    word_num: int


class OCRParagraph(TypedDict):
    text: str
    left: int
    top: int
    width: int
    height: int


class WinRect(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("rcMonitor", WinRect),
        ("rcWork", WinRect),
        ("dwFlags", ctypes.c_ulong),
        ("szDevice", ctypes.c_wchar * 32),
    ]


class TranslatorCore(QObject):
    finished = pyqtSignal(object, object)
    failed = pyqtSignal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._busy = False
        self._lock = threading.Lock()
        resolved_tesseract = resolve_tesseract_executable()
        if resolved_tesseract:
            pytesseract.pytesseract.tesseract_cmd = resolved_tesseract

    def process_selection(self, selection_rect: QRect, profile: TranslationProfile) -> None:
        with self._lock:
            if self._busy:
                return
            self._busy = True
        threading.Thread(target=self._process_worker, args=(QRect(selection_rect), profile), daemon=True).start()

    def _process_worker(self, selection_rect: QRect, profile: TranslationProfile) -> None:
        try:
            capture = self._capture_selection(selection_rect)
            blocks = self._extract_and_translate_blocks(capture, profile)
            self.finished.emit(selection_rect, blocks)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            with self._lock:
                self._busy = False

    def _capture_selection(self, selection_rect: QRect) -> Image.Image:
        if selection_rect.isEmpty():
            raise ValueError("Selection is empty.")

        screen_map = build_screen_mapping()
        if not screen_map:
            raise RuntimeError("No screens detected.")

        canvas = Image.new("RGB", (selection_rect.width(), selection_rect.height()), "white")
        with mss() as sct:
            for screen in screen_map:
                intersection = selection_rect.intersected(screen.logical_geometry)
                if intersection.isEmpty():
                    continue

                physical_box = logical_rect_to_physical_box(intersection, screen)
                if physical_box[2] <= 0 or physical_box[3] <= 0:
                    continue

                shot = sct.grab(
                    {
                        "left": physical_box[0],
                        "top": physical_box[1],
                        "width": physical_box[2],
                        "height": physical_box[3],
                    }
                )
                piece = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

                logical_piece_size = (intersection.width(), intersection.height())
                if piece.size != logical_piece_size:
                    piece = piece.resize(logical_piece_size, Image.Resampling.LANCZOS)

                paste_x = intersection.left() - selection_rect.left()
                paste_y = intersection.top() - selection_rect.top()
                canvas.paste(piece, (paste_x, paste_y))

        return canvas

    def _extract_and_translate_blocks(self, image: Image.Image, profile: TranslationProfile) -> List[TextBlock]:
        data = pytesseract.image_to_data(
            image,
            output_type=Output.DICT,
            lang=profile.ocr_lang,
            config=profile.ocr_config,
        )
        paragraphs = group_ocr_words_into_paragraphs(data)
        if not paragraphs:
            return []

        translated_blocks: List[TextBlock] = []
        translator: Optional[GoogleTranslator] = None
        if profile.translation_source != profile.translation_target or profile.translation_source == "auto":
            translator = GoogleTranslator(source=profile.translation_source, target=profile.translation_target)

        for paragraph in paragraphs:
            text = paragraph["text"]
            if not text.strip():
                continue
            try:
                if translator is None:
                    translated = text
                else:
                    translated = translator.translate(text)
            except Exception:
                translated = text

            translated_blocks.append(
                TextBlock(
                    left=paragraph["left"],
                    top=paragraph["top"],
                    width=paragraph["width"],
                    height=paragraph["height"],
                    original_text=text,
                    translated_text=translated or text,
                )
            )

        translated_blocks.sort(key=lambda block: (block.top, block.left))
        return translated_blocks


class SnippingWidget(QWidget):
    selection_made = pyqtSignal(QRect)
    cancelled = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._dragging = False
        self._selection_start = QPoint()
        self._selection_end = QPoint()
        self._virtual_geometry = virtual_desktop_geometry()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setGeometry(self._virtual_geometry)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self.raise_()
        self.activateWindow()
        self.setFocus()

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            self.close()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._selection_start = event.position().toPoint()
            self._selection_end = self._selection_start
            self.update()
        elif event.button() == Qt.MouseButton.RightButton:
            self.cancelled.emit()
            self.close()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._dragging:
            self._selection_end = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._dragging = False
            self._selection_end = event.position().toPoint()
            selection = self.selection_rect()
            if selection.width() < 8 or selection.height() < 8:
                self.cancelled.emit()
                self.close()
                return
            self.selection_made.emit(selection)
            self.close()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 110))

        if self._dragging or not self.selection_rect().isNull():
            selection = self.selection_rect_local()
            if not selection.isNull():
                painter.fillRect(selection, QColor(80, 170, 255, 70))
                pen = QPen(QColor(90, 200, 255), 2)
                pen.setCosmetic(True)
                painter.setPen(pen)
                painter.drawRect(selection.adjusted(0, 0, -1, -1))

        painter.end()

    def selection_rect_local(self) -> QRect:
        if self._selection_start.isNull() and self._selection_end.isNull():
            return QRect()
        return QRect(self._selection_start, self._selection_end).normalized()

    def selection_rect(self) -> QRect:
        rect = self.selection_rect_local()
        rect.translate(self.geometry().topLeft())
        return rect


class OverlayTextLabel(QLabel):
    clicked = pyqtSignal(int)

    def __init__(self, block_index: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._block_index = block_index
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._block_index)
            event.accept()
            return
        super().mousePressEvent(event)


class OverlayWidget(QWidget):
    closed = pyqtSignal()

    def __init__(self, selection_rect: QRect, blocks: List[TextBlock], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._selection_rect = QRect(selection_rect)
        self._blocks = blocks
        self._selected_index = -1
        self._label_style = (
            "background-color: #fff2a8;"
            "color: #111111;"
            "border: 1px solid rgba(0, 0, 0, 45);"
            "border-radius: 4px;"
            "padding: 2px 4px;"
        )
        self._label_selected_style = (
            "background-color: #fff7cc;"
            "color: #111111;"
            "border: 2px solid #2563eb;"
            "border-radius: 4px;"
            "padding: 1px 3px;"
        )

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setGeometry(self._selection_rect)
        self._build_ui()

    def _build_ui(self) -> None:
        self._labels: List[QLabel] = []
        font = QFont("Segoe UI", 11)
        metrics = QFontMetrics(font)
        for index, block in enumerate(self._blocks):
            label = OverlayTextLabel(index, self)
            label.setTextFormat(Qt.TextFormat.PlainText)
            label.setWordWrap(True)
            label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            label.setFont(font)
            label.setToolTip("Click to select this block for Copy Sel")
            text_width = max(1, block.width - 8)
            text_rect = metrics.boundingRect(0, 0, text_width, 2000, Qt.TextFlag.TextWordWrap, block.translated_text)
            label_height = max(block.height, text_rect.height() + 6)
            label.setGeometry(block.left, block.top, max(1, block.width), max(1, label_height))
            label.setText(block.translated_text)
            label.clicked.connect(self._select_block)
            label.setStyleSheet(self._label_style)
            label.show()
            self._labels.append(label)

        self._copy_all_button = QPushButton("All", self)
        self._copy_all_button.setToolTip("Copy all translated text")
        self._copy_all_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_all_button.setFixedSize(36, 28)
        self._copy_all_button.setStyleSheet(
            "QPushButton {"
            "background-color: rgba(20, 20, 20, 220);"
            "color: white;"
            "border: 1px solid rgba(255, 255, 255, 50);"
            "border-radius: 8px;"
            "font: bold 11px 'Segoe UI';"
            "}"
            "QPushButton:hover { background-color: rgba(60, 60, 60, 235); }"
        )
        self._copy_all_button.clicked.connect(self.copy_all_text)

        self._copy_selected_button = QPushButton("Sel", self)
        self._copy_selected_button.setToolTip("Copy selected translated text")
        self._copy_selected_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_selected_button.setFixedSize(36, 28)
        self._copy_selected_button.setStyleSheet(
            "QPushButton {"
            "background-color: rgba(20, 20, 20, 220);"
            "color: white;"
            "border: 1px solid rgba(255, 255, 255, 50);"
            "border-radius: 8px;"
            "font: bold 11px 'Segoe UI';"
            "}"
            "QPushButton:hover { background-color: rgba(60, 60, 60, 235); }"
        )
        self._copy_selected_button.clicked.connect(self.copy_selected_text)

        self._close_button = QPushButton("X", self)
        self._close_button.setToolTip("Close overlay")
        self._close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_button.setFixedSize(28, 28)
        self._close_button.setStyleSheet(
            "QPushButton {"
            "background-color: rgba(20, 20, 20, 220);"
            "color: white;"
            "border: 1px solid rgba(255, 255, 255, 50);"
            "border-radius: 14px;"
            "font: bold 16px 'Segoe UI';"
            "}"
            "QPushButton:hover { background-color: rgba(60, 60, 60, 235); }"
        )
        self._close_button.clicked.connect(self.close)
        self._update_action_buttons_state()
        if self._labels:
            self._select_block(0)
        self._position_controls()
        self._copy_all_button.show()
        self._copy_selected_button.show()
        self._close_button.show()

    def _position_controls(self) -> None:
        margin = 8
        gap = 6
        total_width = (
            self._copy_all_button.width()
            + gap
            + self._copy_selected_button.width()
            + gap
            + self._close_button.width()
        )
        all_x = max(margin, self.width() - margin - total_width)
        selected_x = all_x + self._copy_all_button.width() + gap
        close_x = selected_x + self._copy_selected_button.width() + gap
        self._copy_all_button.move(all_x, margin)
        self._copy_selected_button.move(selected_x, margin)
        self._close_button.move(close_x, margin)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._position_controls()

    def _select_block(self, index: int) -> None:
        if index < 0 or index >= len(self._labels):
            return
        self._selected_index = index
        for label_index, label in enumerate(self._labels):
            label.setStyleSheet(self._label_selected_style if label_index == index else self._label_style)
        self._update_action_buttons_state()

    def _update_action_buttons_state(self) -> None:
        has_blocks = bool(self._blocks)
        self._copy_all_button.setEnabled(has_blocks)
        self._copy_selected_button.setEnabled(has_blocks and self._selected_index >= 0)

    def _copy_to_clipboard(self, text: str) -> None:
        if not text.strip():
            return
        clipboard = cast(Any, QApplication.clipboard())
        clipboard.setText(text)

    def copy_all_text(self) -> None:
        lines = [block.translated_text.strip() for block in self._blocks if block.translated_text.strip()]
        self._copy_to_clipboard("\n".join(lines))

    def copy_selected_text(self) -> None:
        if self._selected_index < 0 or self._selected_index >= len(self._blocks):
            return
        self._copy_to_clipboard(self._blocks[self._selected_index].translated_text)

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.closed.emit()
        super().closeEvent(event)


class TrayIcon(QObject):
    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self._app = app
        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(build_tray_icon())

        self._translator = TranslatorCore(self)
        self._translator.finished.connect(self._show_overlay)
        self._translator.failed.connect(self._show_error)

        self._settings = QSettings()
        self._source_language_key = self._load_language_key("language/source", DEFAULT_SOURCE_LANGUAGE_KEY, SOURCE_LANGUAGE_KEYS)
        self._target_language_key = self._load_language_key("language/target", DEFAULT_TARGET_LANGUAGE_KEY, TARGET_LANGUAGE_KEYS)

        self._snipping_widget: Optional[SnippingWidget] = None
        self._overlay_widget: Optional[OverlayWidget] = None
        self._hotkey_service = GlobalHotkeyService(self)
        self._hotkey_service.triggered.connect(self.trigger_snipping)
        self._hotkey_service.error.connect(self._show_error)

        self._menu = QMenu()
        self._action_snip = QAction("Snipping mode (Ctrl+Shift+E)", self._menu)
        self._action_snip.triggered.connect(self.trigger_snipping)
        self._menu.addAction(self._action_snip)
        self._menu.addSeparator()

        self._source_menu = cast(QMenu, self._menu.addMenu("Source OCR language"))
        self._target_menu = cast(QMenu, self._menu.addMenu("Target translation language"))
        self._source_action_group = QActionGroup(self)
        self._source_action_group.setExclusive(True)
        self._target_action_group = QActionGroup(self)
        self._target_action_group.setExclusive(True)
        self._source_actions: Dict[str, QAction] = {}
        self._target_actions: Dict[str, QAction] = {}
        self._build_language_menus()

        self._menu.addSeparator()
        self._action_quit = QAction("Quit", self._menu)
        self._action_quit.triggered.connect(self.quit)
        self._menu.addAction(self._action_quit)
        self._tray.setContextMenu(self._menu)
        self._update_ui_for_language_change()

        self._install_hotkey()
        self._tray.show()

    def _load_language_key(self, setting_key: str, default_key: str, allowed_keys: Tuple[str, ...]) -> str:
        value = str(self._settings.value(setting_key, default_key)).strip()
        return value if value in allowed_keys else default_key

    def _build_language_menus(self) -> None:
        self._source_menu.clear()
        self._target_menu.clear()
        self._source_actions.clear()
        self._target_actions.clear()

        for choice in LANGUAGE_CHOICES:
            action = QAction(choice.label, self._source_menu)
            action.setCheckable(True)
            action.setChecked(choice.key == self._source_language_key)
            action.triggered.connect(lambda checked=False, key=choice.key: self.set_source_language(key))
            self._source_action_group.addAction(action)
            self._source_menu.addAction(action)
            self._source_actions[choice.key] = action

        for choice in (item for item in LANGUAGE_CHOICES if item.key != "auto"):
            action = QAction(choice.label, self._target_menu)
            action.setCheckable(True)
            action.setChecked(choice.key == self._target_language_key)
            action.triggered.connect(lambda checked=False, key=choice.key: self.set_target_language(key))
            self._target_action_group.addAction(action)
            self._target_menu.addAction(action)
            self._target_actions[choice.key] = action

    def _update_ui_for_language_change(self) -> None:
        self._source_menu.setTitle(f"Source OCR language: {language_choice_for_key(self._source_language_key).label}")
        self._target_menu.setTitle(f"Target translation language: {language_choice_for_key(self._target_language_key).label}")
        self._tray.setToolTip(self._build_tooltip())
        for key, action in self._source_actions.items():
            action.setChecked(key == self._source_language_key)
        for key, action in self._target_actions.items():
            action.setChecked(key == self._target_language_key)

    def _build_tooltip(self) -> str:
        source_label = language_choice_for_key(self._source_language_key).label
        target_label = language_choice_for_key(self._target_language_key).label
        return f"{APP_NAME} | Source: {source_label} | Target: {target_label}"

    def set_source_language(self, language_key: str) -> None:
        if language_key not in SOURCE_LANGUAGE_KEYS:
            return
        self._source_language_key = language_key
        self._settings.setValue("language/source", language_key)
        self._update_ui_for_language_change()
        self._tray.showMessage(
            APP_NAME,
            f"Source OCR language set to {language_choice_for_key(language_key).label}",
            QSystemTrayIcon.MessageIcon.Information,
            2500,
        )

    def set_target_language(self, language_key: str) -> None:
        if language_key not in TARGET_LANGUAGE_KEYS:
            return
        self._target_language_key = language_key
        self._settings.setValue("language/target", language_key)
        self._update_ui_for_language_change()
        self._tray.showMessage(
            APP_NAME,
            f"Target language set to {language_choice_for_key(language_key).label}",
            QSystemTrayIcon.MessageIcon.Information,
            2500,
        )

    def _install_hotkey(self) -> None:
        self._hotkey_service.start()

    def trigger_snipping(self) -> None:
        if self._snipping_widget is not None:
            return
        if self._overlay_widget is not None:
            self._overlay_widget.close()
            self._overlay_widget = None

        self._snipping_widget = SnippingWidget()
        self._snipping_widget.selection_made.connect(self._on_selection_made)
        self._snipping_widget.cancelled.connect(self._on_snipping_cancelled)
        self._snipping_widget.destroyed.connect(lambda *_: self._clear_snipping_reference())
        self._snipping_widget.show()
        self._snipping_widget.raise_()
        self._snipping_widget.activateWindow()

    def _clear_snipping_reference(self) -> None:
        self._snipping_widget = None

    def _on_snipping_cancelled(self) -> None:
        self._clear_snipping_reference()

    def _on_selection_made(self, selection_rect: QRect) -> None:
        self._clear_snipping_reference()
        profile = build_translation_profile(self._source_language_key, self._target_language_key)
        self._translator.process_selection(selection_rect, profile)

    def _show_overlay(self, selection_rect: QRect, blocks: List[TextBlock]) -> None:
        if self._overlay_widget is not None:
            self._overlay_widget.close()
        self._overlay_widget = OverlayWidget(selection_rect, blocks)
        self._overlay_widget.closed.connect(self._on_overlay_closed)
        self._overlay_widget.show()
        self._overlay_widget.raise_()
        self._overlay_widget.activateWindow()

    def _on_overlay_closed(self) -> None:
        self._overlay_widget = None

    def _show_error(self, message: str) -> None:
        self._tray.showMessage(APP_NAME, message, QSystemTrayIcon.MessageIcon.Critical, 5000)
        print(message, file=sys.stderr)

    def quit(self) -> None:
        self.shutdown()
        self._app.quit()

    def shutdown(self) -> None:
        self._hotkey_service.stop()
        if self._overlay_widget is not None:
            self._overlay_widget.close()
            self._overlay_widget = None
        if self._snipping_widget is not None:
            self._snipping_widget.close()
            self._snipping_widget = None


def build_tray_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setBrush(QBrush(QColor("#1c7ed6")))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(8, 8, 48, 48, 12, 12)
    painter.setPen(QPen(QColor("white")))
    font = QFont("Segoe UI", 18, QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "ST")
    painter.end()
    return QIcon(pixmap)


def normalize_display_name(name: str) -> str:
    return name.replace("\\.\\", "").replace(" ", "").upper()


def get_windows_monitor_infos() -> List[WindowsMonitorInfo]:
    user32 = ctypes.windll.user32
    monitors: List[WindowsMonitorInfo] = []

    MonitorEnumProc = ctypes.WINFUNCTYPE(
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.POINTER(WinRect),
        ctypes.c_long,
    )

    def _callback(hmonitor, hdc, lprc, lparam):  # noqa: ANN001
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(MONITORINFOEXW)
        if user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
            monitors.append(
                WindowsMonitorInfo(
                    device_name=info.szDevice,
                    physical_geometry=QRect(
                        info.rcMonitor.left,
                        info.rcMonitor.top,
                        info.rcMonitor.right - info.rcMonitor.left,
                        info.rcMonitor.bottom - info.rcMonitor.top,
                    ),
                )
            )
        return 1

    callback = MonitorEnumProc(_callback)
    if not user32.EnumDisplayMonitors(None, None, callback, None):
        raise ctypes.WinError()

    return monitors


def build_screen_mapping() -> List[ScreenInfo]:
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        return []

    qt_screens = list(app.screens())
    win_monitors = get_windows_monitor_infos() if sys.platform.startswith("win") else []

    mappings: List[ScreenInfo] = []
    used_indices: set[int] = set()

    for screen in qt_screens:
        logical = QRect(screen.geometry())
        dpr = float(screen.devicePixelRatio()) or 1.0
        scale_x = dpr
        scale_y = dpr
        physical = QRect(
            int(round(logical.x() * scale_x)),
            int(round(logical.y() * scale_y)),
            int(round(logical.width() * scale_x)),
            int(round(logical.height() * scale_y)),
        )

        matched_index = None
        normalized = normalize_display_name(screen.name())
        for index, monitor in enumerate(win_monitors):
            if index in used_indices:
                continue
            monitor_name = normalize_display_name(monitor.device_name)
            if normalized and normalized == monitor_name:
                matched_index = index
                break

        if matched_index is not None:
            monitor = win_monitors[matched_index]
            used_indices.add(matched_index)
            physical = monitor.physical_geometry
            if logical.width() > 0:
                scale_x = physical.width() / logical.width()
            if logical.height() > 0:
                scale_y = physical.height() / logical.height()
        else:
            if logical.width() > 0 and logical.height() > 0:
                physical = QRect(
                    int(round(logical.x() * scale_x)),
                    int(round(logical.y() * scale_y)),
                    int(round(logical.width() * scale_x)),
                    int(round(logical.height() * scale_y)),
                )

        mappings.append(
            ScreenInfo(
                device_name=screen.name(),
                logical_geometry=logical,
                physical_geometry=physical,
                scale_x=scale_x,
                scale_y=scale_y,
            )
        )

    return mappings


def logical_rect_to_physical_box(rect: QRect, screen: ScreenInfo) -> Tuple[int, int, int, int]:
    logical = screen.logical_geometry
    physical = screen.physical_geometry

    offset_x = rect.left() - logical.left()
    offset_y = rect.top() - logical.top()

    left = physical.left() + int(round(offset_x * screen.scale_x))
    top = physical.top() + int(round(offset_y * screen.scale_y))
    width = int(round(rect.width() * screen.scale_x))
    height = int(round(rect.height() * screen.scale_y))
    return left, top, width, height


class GlobalHotkeyService(QObject):
    triggered = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._thread_id: int = 0
        self._registered = False
        self._keyboard_handle: Any = None

    def start(self) -> None:
        if sys.platform.startswith("win"):
            self._thread = threading.Thread(target=self._windows_message_loop, daemon=True)
            self._thread.start()
            return
        self._register_keyboard_fallback()

    def stop(self) -> None:
        self._stop_event.set()

        if self._registered and self._thread_id:
            try:
                ctypes.windll.user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)
            except Exception:
                pass

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=1.0)

        if self._keyboard_handle is not None and keyboard is not None:
            try:
                keyboard.remove_hotkey(self._keyboard_handle)
            except Exception:
                try:
                    keyboard.clear_all_hotkeys()
                except Exception:
                    pass
            self._keyboard_handle = None

    def _register_keyboard_fallback(self) -> None:
        if keyboard is None:
            self.error.emit("Global hotkey registration failed and the keyboard module is unavailable.")
            return
        try:
            self._keyboard_handle = keyboard.add_hotkey(HOTKEY, self.triggered.emit, suppress=True)
        except Exception as exc:
            self.error.emit(f"Failed to register hotkey '{HOTKEY}': {exc}")

    def _windows_message_loop(self) -> None:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        self._thread_id = kernel32.GetCurrentThreadId()

        if not user32.RegisterHotKey(None, HOTKEY_ID, HOTKEY_MODIFIERS, HOTKEY_VK):
            error_code = ctypes.get_last_error()
            self.error.emit(f"Failed to register hotkey '{HOTKEY}': {ctypes.WinError(error_code)}")
            self._register_keyboard_fallback()
            return

        self._registered = True
        message = wintypes.MSG()

        try:
            while not self._stop_event.is_set():
                result = user32.GetMessageW(ctypes.byref(message), None, 0, 0)
                if result == 0:
                    break
                if result == -1:
                    error_code = ctypes.get_last_error()
                    self.error.emit(f"Hotkey message loop failed: {ctypes.WinError(error_code)}")
                    break
                if message.message == 0x0312 and message.wParam == HOTKEY_ID:
                    self.triggered.emit()
        finally:
            if self._registered:
                try:
                    user32.UnregisterHotKey(None, HOTKEY_ID)
                except Exception:
                    pass
                self._registered = False


def virtual_desktop_geometry() -> QRect:
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        return QRect()
    geometry = QRect()
    for screen in app.screens():
        geometry = geometry.united(screen.geometry()) if not geometry.isNull() else QRect(screen.geometry())
    return geometry


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def safe_float(value: Any, default: float = -1.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        return str(value)
    except Exception:
        return default


def group_ocr_words_into_paragraphs(data: Dict[str, List[object]]) -> List[OCRParagraph]:
    groups: Dict[Tuple[int, int], List[OCRWord]] = {}
    texts = cast(List[object], data.get("text", []))
    confs = cast(List[object], data.get("conf", []))
    lefts = cast(List[object], data.get("left", []))
    tops = cast(List[object], data.get("top", []))
    widths = cast(List[object], data.get("width", []))
    heights = cast(List[object], data.get("height", []))
    block_nums = cast(List[object], data.get("block_num", []))
    par_nums = cast(List[object], data.get("par_num", []))
    line_nums = cast(List[object], data.get("line_num", []))
    word_nums = cast(List[object], data.get("word_num", []))

    total = len(texts)

    for index in range(total):
        raw_text = safe_str(texts[index]).strip()
        if not raw_text:
            continue

        confidence = safe_float(confs[index] if index < len(confs) else -1.0)
        if confidence < OCR_CONFIDENCE_THRESHOLD:
            continue

        left = safe_int(lefts[index] if index < len(lefts) else 0)
        top = safe_int(tops[index] if index < len(tops) else 0)
        width = safe_int(widths[index] if index < len(widths) else 0)
        height = safe_int(heights[index] if index < len(heights) else 0)
        block_num = safe_int(block_nums[index] if index < len(block_nums) else 0)
        par_num = safe_int(par_nums[index] if index < len(par_nums) else 0)
        line_num = safe_int(line_nums[index] if index < len(line_nums) else 0)
        word_num = safe_int(word_nums[index] if index < len(word_nums) else 0)

        key = (block_num, par_num)
        groups.setdefault(key, []).append(
            OCRWord(
                text=raw_text,
                left=left,
                top=top,
                width=width,
                height=height,
                line_num=line_num,
                word_num=word_num,
            )
        )

    paragraphs: List[OCRParagraph] = []
    for words in groups.values():
        words.sort(key=lambda item: (item["line_num"], item["word_num"], item["left"]))
        lines: Dict[int, List[OCRWord]] = {}
        for word in words:
            lines.setdefault(word["line_num"], []).append(word)

        line_texts: List[str] = []
        all_lefts: List[int] = []
        all_tops: List[int] = []
        all_rights: List[int] = []
        all_bottoms: List[int] = []

        for line_num in sorted(lines):
            line_words = sorted(lines[line_num], key=lambda item: (item["word_num"], item["left"]))
            line_text = " ".join(word["text"] for word in line_words).strip()
            if not line_text:
                continue
            line_texts.append(line_text)
            for word in line_words:
                left = word["left"]
                top = word["top"]
                width = word["width"]
                height = word["height"]
                all_lefts.append(left)
                all_tops.append(top)
                all_rights.append(left + width)
                all_bottoms.append(top + height)

        if not line_texts or not all_lefts:
            continue

        paragraphs.append(
            OCRParagraph(
                text="\n".join(line_texts),
                left=min(all_lefts),
                top=min(all_tops),
                width=max(all_rights) - min(all_lefts),
                height=max(all_bottoms) - min(all_tops),
            )
        )

    paragraphs.sort(key=lambda item: (int(item["top"]), int(item["left"])))
    return paragraphs


def configure_process_dpi_awareness() -> None:
    if not sys.platform.startswith("win"):
        return

    try:
        user32 = ctypes.windll.user32
        set_awareness_context = getattr(user32, "SetProcessDpiAwarenessContext", None)
        if set_awareness_context is not None:
            # PER_MONITOR_AWARE_V2 = -4
            set_awareness_context(ctypes.c_void_p(-4))
            return
    except Exception:
        pass

    try:
        shcore = ctypes.windll.shcore
        shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        return
    except Exception:
        pass

    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def show_startup_message() -> None:
    print(f"{APP_NAME} is running. Press Ctrl+Shift+E to snip.")


def main() -> int:
    configure_process_dpi_awareness()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("GitHub Copilot")

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, APP_NAME, "System tray is not available on this desktop.")
        return 1

    tray = TrayIcon(app)
    app.aboutToQuit.connect(tray.shutdown)
    show_startup_message()
    try:
        return app.exec()
    except KeyboardInterrupt:
        tray.shutdown()
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
