"""
TrustSync — Log Panel Widget

Painel de log de auditoria forense com formatação rich-text,
cores por severidade e suporte a exportação.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.ui.styles.theme import COLORS
from src.utils.logger import ForensicLogEntry, ForensicLogger, LogLevel

logger = ForensicLogger()

# Cores por nível de severidade
LEVEL_COLORS = {
    LogLevel.DEBUG: COLORS["text_muted"],
    LogLevel.INFO: COLORS["text_primary"],
    LogLevel.WARNING: COLORS["warning"],
    LogLevel.ERROR: COLORS["error"],
    LogLevel.CRITICAL: COLORS["red"],
}

LEVEL_ICONS = {
    LogLevel.DEBUG: "🔍",
    LogLevel.INFO: "ℹ️",
    LogLevel.WARNING: "⚠️",
    LogLevel.ERROR: "❌",
    LogLevel.CRITICAL: "🚨",
}


class LogPanel(QWidget):
    """
    Painel de log de auditoria forense.

    Exibe logs com formatação rich-text colorida por severidade,
    timestamps ISO-8601 e suporte a exportação para arquivo .txt.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Monta a interface do painel de log."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("📋 Log de Auditoria")
        title.setStyleSheet(
            f"font-size: 14px; font-weight: bold; "
            f"color: {COLORS['accent']}; background: transparent;"
        )

        self._count_label = QLabel("0 entradas")
        self._count_label.setStyleSheet(
            f"font-size: 11px; color: {COLORS['text_muted']}; "
            f"background: transparent;"
        )

        self._export_btn = QPushButton("Exportar")
        self._export_btn.setFixedHeight(28)
        self._export_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['accent']};
                border: 1px solid {COLORS['accent_dim']};
                border-radius: 4px;
                padding: 2px 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_dim']};
                color: white;
            }}
            """
        )

        self._clear_btn = QPushButton("Limpar")
        self._clear_btn.setFixedHeight(28)
        self._clear_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['text_muted']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 2px 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['bg_hover']};
                color: {COLORS['text_primary']};
            }}
            """
        )

        header_layout.addWidget(title)
        header_layout.addWidget(self._count_label)
        header_layout.addStretch()
        header_layout.addWidget(self._export_btn)
        header_layout.addWidget(self._clear_btn)

        # Text area
        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setAcceptRichText(True)
        self._text_edit.setStyleSheet(
            f"""
            QTextEdit {{
                background-color: {COLORS['bg_surface']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px;
                font-family: "Cascadia Code", "Consolas", "Fira Code", monospace;
                font-size: 11px;
            }}
            """
        )

        layout.addLayout(header_layout)
        layout.addWidget(self._text_edit)

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self._entry_count = 0

    def _connect_signals(self):
        """Conecta sinais do logger e botões."""
        logger.signal_emitter.log_emitted.connect(self.append_entry)
        self._export_btn.clicked.connect(self._export_log)
        self._clear_btn.clicked.connect(self._clear_log)

    def append_entry(self, entry: ForensicLogEntry):
        """
        Adiciona uma entrada de log ao painel com formatação colorida.

        Args:
            entry: Entrada de log forense.
        """
        color = LEVEL_COLORS.get(entry.level, COLORS["text_primary"])
        icon = LEVEL_ICONS.get(entry.level, "")

        # Timestamp em cor suave
        timestamp_html = (
            f'<span style="color: {COLORS["text_muted"]}">'
            f"{entry.timestamp}</span>"
        )

        # Nível em negrito e colorido
        level_html = (
            f'<span style="color: {color}; font-weight: bold">'
            f"{icon} {entry.level.value}</span>"
        )

        # Source entre colchetes
        source_html = (
            f'<span style="color: {COLORS["accent_dim"]}">'
            f"[{entry.source}]</span>"
        )

        # Mensagem
        msg_html = f'<span style="color: {color}">{entry.message}</span>'

        html = f"{timestamp_html} {level_html} {source_html} {msg_html}<br/>"
        self._text_edit.insertHtml(html)

        # Auto-scroll para o final
        scrollbar = self._text_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        # Atualizar contador
        self._entry_count += 1
        self._count_label.setText(f"{self._entry_count} entradas")

    def _export_log(self):
        """Exporta o log completo para um arquivo .txt."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Log de Auditoria",
            "trustsync_audit_log.txt",
            "Arquivo de Texto (*.txt)",
        )

        if file_path:
            content = logger.export_to_text()
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(
                f"Log exportado para: {file_path}", source="UI"
            )

    def _clear_log(self):
        """Limpa o painel de log."""
        self._text_edit.clear()
        self._entry_count = 0
        self._count_label.setText("0 entradas")
        logger.clear()
