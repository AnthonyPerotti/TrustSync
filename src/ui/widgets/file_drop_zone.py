"""
TrustSync — File Drop Zone Widget

Área de drag-and-drop para arquivos de mídia com preview
de thumbnail e detecção de tipo de arquivo.
"""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QFont, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.ui.styles.theme import COLORS

# Extensões suportadas por tipo
MEDIA_TYPES = {
    "audio": {
        ".wav", ".mp3", ".flac", ".ogg", ".m4a",
        ".aac", ".wma", ".opus", ".aiff",
    },
    "video": {
        ".mp4", ".avi", ".mkv", ".mov", ".wmv",
        ".flv", ".webm", ".m4v", ".mpeg", ".mpg",
    },
    "document": {
        ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif",
        ".webp", ".heic", ".heif", ".gif",
        ".pdf", ".docx", ".doc",
    },
}

MEDIA_ICONS = {
    "audio": "🎵",
    "video": "🎬",
    "document": "📄",
    "unknown": "📁",
}

ALL_EXTENSIONS = set()
for exts in MEDIA_TYPES.values():
    ALL_EXTENSIONS.update(exts)


def detect_media_type(file_path: str | Path) -> str:
    """Detecta o tipo de mídia com base na extensão."""
    ext = Path(file_path).suffix.lower()
    for media_type, extensions in MEDIA_TYPES.items():
        if ext in extensions:
            return media_type
    return "unknown"


class FileDropZone(QWidget):
    """
    Zona de drag-and-drop para seleção de arquivos de mídia.

    Emite:
        - file_selected(str): Caminho absoluto do arquivo selecionado
    """

    file_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._setup_ui()

    def _setup_ui(self):
        """Monta a interface da zona de drop."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # Ícone grande
        self._icon_label = QLabel("📂")
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setFont(QFont("Segoe UI Emoji", 48))
        self._icon_label.setStyleSheet("background: transparent;")

        # Texto principal
        self._title_label = QLabel("Arraste um arquivo aqui")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setStyleSheet(
            f"font-size: 16px; font-weight: bold; "
            f"color: {COLORS['text_primary']}; background: transparent;"
        )

        # Texto secundário
        self._subtitle_label = QLabel(
            "Áudio · Vídeo · Imagens · Documentos"
        )
        self._subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._subtitle_label.setStyleSheet(
            f"font-size: 12px; color: {COLORS['text_muted']}; "
            f"background: transparent;"
        )

        # Botão de seleção
        self._select_btn = QPushButton("Selecionar Arquivo")
        self._select_btn.setFixedSize(180, 40)
        self._select_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._select_btn.clicked.connect(self._open_file_dialog)

        # Info do arquivo selecionado (oculto inicialmente)
        self._file_info_label = QLabel("")
        self._file_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._file_info_label.setWordWrap(True)
        self._file_info_label.setStyleSheet(
            f"font-size: 12px; color: {COLORS['accent']}; "
            f"background: transparent;"
        )
        self._file_info_label.hide()

        # Thumbnail (oculto inicialmente)
        self._thumbnail_label = QLabel()
        self._thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumbnail_label.setFixedSize(120, 120)
        self._thumbnail_label.setStyleSheet(
            f"background: transparent; border: 1px solid {COLORS['border']}; "
            f"border-radius: 8px;"
        )
        self._thumbnail_label.hide()

        layout.addStretch()
        layout.addWidget(self._icon_label)
        layout.addWidget(self._title_label)
        layout.addWidget(self._subtitle_label)
        layout.addWidget(
            self._select_btn, alignment=Qt.AlignmentFlag.AlignCenter
        )
        layout.addWidget(self._thumbnail_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._file_info_label)
        layout.addStretch()

        # Estilo base da zona
        self._update_border_style(False)

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

    def _update_border_style(self, is_hover: bool):
        """Atualiza o estilo de borda (normal vs hover de drag)."""
        if is_hover:
            self.setStyleSheet(
                f"""
                FileDropZone {{
                    background-color: {COLORS['bg_tertiary']};
                    border: 2px dashed {COLORS['accent']};
                    border-radius: 16px;
                }}
                """
            )
        else:
            self.setStyleSheet(
                f"""
                FileDropZone {{
                    background-color: {COLORS['bg_secondary']};
                    border: 2px dashed {COLORS['border']};
                    border-radius: 16px;
                }}
                """
            )

    # ── Drag & Drop ──

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Aceita o drag se contiver URLs de arquivo."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].isLocalFile():
                file_path = urls[0].toLocalFile()
                ext = Path(file_path).suffix.lower()
                if ext in ALL_EXTENSIONS:
                    event.acceptProposedAction()
                    self._update_border_style(True)
                    return
        event.ignore()

    def dragLeaveEvent(self, event):
        """Restaura estilo quando o drag sai da zona."""
        self._update_border_style(False)

    def dropEvent(self, event: QDropEvent):
        """Processa o arquivo dropado."""
        self._update_border_style(False)

        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            if url.isLocalFile():
                file_path = url.toLocalFile()
                self._handle_file_selected(file_path)
                event.acceptProposedAction()

    # ── File Selection ──

    def _open_file_dialog(self):
        """Abre diálogo de seleção de arquivo."""
        ext_filter = "Arquivos de Mídia ("
        ext_filter += " ".join(f"*{ext}" for ext in sorted(ALL_EXTENSIONS))
        ext_filter += ")"

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Arquivo para Análise",
            "",
            ext_filter,
        )

        if file_path:
            self._handle_file_selected(file_path)

    def _handle_file_selected(self, file_path: str):
        """Processa o arquivo selecionado e atualiza a UI."""
        path = Path(file_path)
        media_type = detect_media_type(path)
        icon = MEDIA_ICONS.get(media_type, "📁")
        size_mb = path.stat().st_size / (1024 * 1024)

        # Atualizar ícone
        self._icon_label.setText(icon)

        # Atualizar info
        self._title_label.setText(path.name)
        self._title_label.setStyleSheet(
            f"font-size: 14px; font-weight: bold; "
            f"color: {COLORS['accent']}; background: transparent;"
        )
        self._subtitle_label.setText(
            f"{media_type.upper()} · {size_mb:.1f} MB"
        )

        # Thumbnail para imagens
        if media_type == "document" and path.suffix.lower() in {
            ".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"
        }:
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    120, 120,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._thumbnail_label.setPixmap(scaled)
                self._thumbnail_label.show()
            else:
                self._thumbnail_label.hide()
        else:
            self._thumbnail_label.hide()

        self._file_info_label.setText(str(path))
        self._file_info_label.show()

        # Emitir sinal
        self.file_selected.emit(str(path))
