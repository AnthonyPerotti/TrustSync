"""
TrustSync — Entry Point

Ponto de entrada da aplicação TrustSync.
Inicializa QApplication, aplica o tema escuro forense
e exibe a janela principal.
"""

import os
import subprocess
import sys

# Patch global para garantir que nenhum subprocesso (ExifTool, FFmpeg/ffprobe via librosa, etc.)
# abra janela de terminal no Windows ao rodar o aplicativo (.exe em modo GUI sem console)
if os.name == "nt":
    _orig_popen = subprocess.Popen
    def _patched_popen(*args, **kwargs):
        if "creationflags" not in kwargs or not kwargs["creationflags"]:
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        return _orig_popen(*args, **kwargs)
    subprocess.Popen = _patched_popen

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from src.ui.main_window import MainWindow
from src.ui.styles.theme import get_stylesheet


def main():
    """Inicializa e executa a aplicação TrustSync."""
    # Habilitar High-DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)

    # Configurar fonte padrão
    font = QFont("Segoe UI", 10)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    app.setFont(font)

    # Aplicar tema escuro forense
    app.setStyleSheet(get_stylesheet())

    # Metadados da aplicação
    app.setApplicationName("TrustSync")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("TrustSync")

    # Criar e exibir janela principal
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
