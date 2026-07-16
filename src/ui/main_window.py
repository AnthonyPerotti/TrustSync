"""
TrustSync — Main Window

Janela principal da aplicação com layout de 3 painéis:
  - Esquerda: FileDropZone (seleção de arquivo)
  - Centro: TrafficLight (semáforo de resultado)
  - Direita: LogPanel (log de auditoria)
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenuBar,
    QProgressBar,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from src.controller.scan_controller import ScanController
from src.engine.base_scanner import ScanResult
from src.ui.styles.theme import COLORS
from src.ui.widgets.file_drop_zone import FileDropZone
from src.ui.widgets.log_panel import LogPanel
from src.ui.widgets.traffic_light import TrafficLightWidget
from src.utils.logger import ForensicLogger

logger = ForensicLogger()


class MainWindow(QMainWindow):
    """
    Janela principal do TrustSync.

    Layout:
    ┌───────────────────────────────────────────────────┐
    │  Menu Bar                                         │
    ├──────────┬──────────────────┬─────────────────────┤
    │          │                  │                     │
    │  File    │   Traffic Light  │    Log Panel         │
    │  Drop    │   (Semáforo)     │    (Auditoria)       │
    │  Zone    │                  │                     │
    │          │   Score: 85.2%   │    [timestamp] ...   │
    │          │   AUTÊNTICO      │    [timestamp] ...   │
    │          │                  │                     │
    ├──────────┴──────────────────┴─────────────────────┤
    │  [████████████████░░░░░░] 75%  Analisando...      │
    ├───────────────────────────────────────────────────┤
    │  Status: 🟢 GPU (CUDA)  │  v0.1.0                │
    └───────────────────────────────────────────────────┘
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TrustSync — Perícia Forense de Mídia")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 780)

        # Controller
        self._controller = ScanController()

        # Widgets
        self._setup_menu_bar()
        self._setup_central_widget()
        self._setup_status_bar()
        self._connect_signals()

        logger.info("TrustSync inicializado", source="UI")

    def _setup_menu_bar(self):
        """Cria a barra de menus."""
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        # Menu Arquivo
        file_menu = menu_bar.addMenu("&Arquivo")

        open_action = QAction("&Abrir Arquivo...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_file)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        exit_action = QAction("&Sair", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Menu Ferramentas
        tools_menu = menu_bar.addMenu("&Ferramentas")

        export_log_action = QAction("&Exportar Log...", self)
        export_log_action.setShortcut("Ctrl+E")
        tools_menu.addAction(export_log_action)

        # Menu Sobre
        about_menu = menu_bar.addMenu("&Sobre")

        about_action = QAction("Sobre o &TrustSync", self)
        about_menu.addAction(about_action)

    def _setup_central_widget(self):
        """Monta o layout central com 3 painéis."""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 8)
        main_layout.setSpacing(8)

        # ── Header ──
        header_layout = QHBoxLayout()

        app_title = QLabel("🔒 TrustSync")
        app_title.setObjectName("title")

        app_subtitle = QLabel(
            "Perícia Forense de Mídia · Detecção de Manipulação por IA"
        )
        app_subtitle.setObjectName("subtitle")

        header_layout.addWidget(app_title)
        header_layout.addWidget(app_subtitle)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # ── Splitter com 3 painéis ──
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet(
            f"""
            QSplitter::handle {{
                background-color: {COLORS['border']};
                margin: 4px 2px;
            }}
            QSplitter::handle:hover {{
                background-color: {COLORS['accent_dim']};
            }}
            """
        )

        # Painel esquerdo: File Drop Zone
        self._file_drop_zone = FileDropZone()
        splitter.addWidget(self._file_drop_zone)

        # Painel central: Traffic Light
        traffic_container = QWidget()
        traffic_container.setObjectName("panel")
        traffic_container.setStyleSheet(
            f"""
            QWidget#panel {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
            """
        )
        traffic_layout = QVBoxLayout(traffic_container)
        traffic_layout.setContentsMargins(8, 12, 8, 12)

        traffic_title = QLabel("Resultado da Análise")
        traffic_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        traffic_title.setStyleSheet(
            f"font-size: 13px; font-weight: bold; "
            f"color: {COLORS['accent']}; background: transparent;"
        )

        self._traffic_light = TrafficLightWidget()

        traffic_layout.addWidget(traffic_title)
        traffic_layout.addWidget(self._traffic_light)

        splitter.addWidget(traffic_container)

        # Painel direito: Log Panel
        self._log_panel = LogPanel()
        splitter.addWidget(self._log_panel)

        # Proporções: 30% | 30% | 40%
        splitter.setSizes([320, 320, 440])

        main_layout.addWidget(splitter, stretch=1)

        # ── Progress bar ──
        progress_layout = QHBoxLayout()

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(10)
        self._progress_bar.setTextVisible(False)

        self._stage_label = QLabel("Pronto")
        self._stage_label.setStyleSheet(
            f"font-size: 11px; color: {COLORS['text_muted']}; "
            f"background: transparent;"
        )

        progress_layout.addWidget(self._progress_bar, stretch=1)
        progress_layout.addWidget(self._stage_label)

        main_layout.addLayout(progress_layout)

    def _setup_status_bar(self):
        """Configura a barra de status com info do dispositivo."""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

        # Indicador de dispositivo
        device_name = self._controller.get_device_display_name()
        device_label = QLabel(f"  {device_name}  ")
        device_label.setStyleSheet(
            f"font-size: 11px; color: {COLORS['text_secondary']}; "
            f"background: transparent;"
        )
        status_bar.addPermanentWidget(device_label)

        # Versão
        from src import __version__
        version_label = QLabel(f"  v{__version__}  ")
        version_label.setStyleSheet(
            f"font-size: 11px; color: {COLORS['text_muted']}; "
            f"background: transparent;"
        )
        status_bar.addPermanentWidget(version_label)

    def _connect_signals(self):
        """Conecta sinais entre widgets e controller."""
        # FileDropZone → Controller
        self._file_drop_zone.file_selected.connect(
            self._on_file_selected
        )

        # Controller → UI
        self._controller.scan_started.connect(self._on_scan_started)
        self._controller.scan_progress.connect(self._on_scan_progress)
        self._controller.scan_completed.connect(self._on_scan_completed)
        self._controller.scan_error.connect(self._on_scan_error)
        self._controller.scan_stage.connect(self._on_scan_stage)

    # ── Event Handlers ──

    def _on_open_file(self):
        """Handler do menu Abrir Arquivo."""
        self._file_drop_zone._open_file_dialog()

    def _on_file_selected(self, file_path: str):
        """Handler quando um arquivo é selecionado."""
        self._controller.start_scan(file_path)

    def _on_scan_started(self, file_path: str):
        """Handler quando o scan inicia."""
        self._traffic_light.set_scanning()
        self._progress_bar.setValue(0)
        self._stage_label.setText(f"Analisando: {Path(file_path).name}")

    def _on_scan_progress(self, progress: int):
        """Handler de progresso do scan."""
        self._progress_bar.setValue(progress)

    def _on_scan_completed(self, result: ScanResult):
        """Handler quando o scan é concluído."""
        self._traffic_light.set_score(result.confidence_score)
        self._progress_bar.setValue(100)
        self._stage_label.setText(
            f"Concluído: {Path(result.file_path).name} "
            f"({result.processing_time_ms:.0f}ms)"
        )

    def _on_scan_error(self, error_message: str):
        """Handler de erro no scan."""
        self._traffic_light.set_error("Erro na análise")
        self._progress_bar.setValue(0)
        self._stage_label.setText("Erro")
        logger.error(error_message, source="UI")

    def _on_scan_stage(self, stage: str):
        """Handler de mudança de etapa."""
        self._stage_label.setText(stage)
