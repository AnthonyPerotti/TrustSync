"""
TrustSync — Scan Controller

Orquestra a pipeline de triagem forense, gerenciando workers
e comunicação entre a Engine Layer e a UI Layer.

Pipeline de triagem:
  1. Validar arquivo de entrada
  2. Lançar ScanWorker em thread separada
  3. Coletar resultado e emitir sinais para a UI
  4. Manter histórico de scans na sessão
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal

from src.controller.worker import ScanWorker
from src.engine.base_scanner import ScanResult
from src.engine.runtime_manager import RuntimeManager
from src.utils.logger import ForensicLogger
from src.utils.paths import get_base_path, get_model_path

logger = ForensicLogger()

# Caminhos padrão dos modelos resolvidos de forma portátil (standalone/PyInstaller)
MODELS_DIR = get_base_path() / "src" / "models"
AUDIO_MODEL = get_model_path("wav2vec2_deepfake.onnx")
VIDEO_MODEL = get_model_path("mobilenetv3_deepfake.onnx")


@dataclass
class ScanHistoryEntry:
    """Entrada no histórico de scans da sessão."""
    timestamp: str
    file_name: str
    file_path: str
    result: Optional[ScanResult] = None


class ScanController(QObject):
    """
    Controlador principal da pipeline de análise forense.

    Gerencia o ciclo de vida dos workers, mantém histórico
    de scans e emite sinais para atualizar a UI.

    Sinais:
        - scan_started(str): Path do arquivo sendo analisado
        - scan_progress(int): Progresso da análise (0-100)
        - scan_completed(object): ScanResult com resultado
        - scan_error(str): Mensagem de erro
        - scan_stage(str): Nome da etapa atual
    """

    scan_started = Signal(str)
    scan_progress = Signal(int)
    scan_completed = Signal(object)
    scan_error = Signal(str)
    scan_stage = Signal(str)

    # Extensões suportadas (todas as extensões de todos os scanners)
    SUPPORTED_EXTENSIONS = {
        # Áudio
        ".wav", ".mp3", ".flac", ".ogg", ".m4a",
        ".aac", ".wma", ".opus", ".aiff",
        # Vídeo
        ".mp4", ".avi", ".mkv", ".mov", ".wmv",
        ".flv", ".webm", ".m4v", ".mpeg", ".mpg",
        # Documentos / Imagens
        ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif",
        ".webp", ".heic", ".heif", ".gif",
        ".pdf", ".docx", ".doc",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_worker: Optional[ScanWorker] = None
        self._history: list[ScanHistoryEntry] = []
        self._runtime = RuntimeManager()

    def start_scan(self, file_path: str):
        """
        Inicia uma análise forense em um arquivo.

        Valida o arquivo, cria um ScanWorker e o executa
        em uma thread separada.

        Args:
            file_path: Caminho absoluto para o arquivo.
        """
        path = Path(file_path)

        # Validações
        if not path.exists():
            self.scan_error.emit(f"Arquivo não encontrado: {path}")
            return

        if not path.is_file():
            self.scan_error.emit(f"Caminho não é um arquivo: {path}")
            return

        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            self.scan_error.emit(
                f"Tipo de arquivo não suportado: {path.suffix}\n"
                f"Extensões suportadas: {', '.join(sorted(self.SUPPORTED_EXTENSIONS))}"
            )
            return

        # Cancelar scan em andamento, se houver
        if self._current_worker and self._current_worker.isRunning():
            logger.warning(
                "Cancelando scan anterior em andamento",
                source="CONTROLLER",
            )
            self._current_worker.cancel()
            self._current_worker.wait(3000)

        # Registrar início no histórico
        entry = ScanHistoryEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            file_name=path.name,
            file_path=str(path),
        )
        self._history.append(entry)

        logger.info(
            f"Iniciando scan de '{path.name}'", source="CONTROLLER"
        )

        # Emitir sinal de início
        self.scan_started.emit(str(path))

        # Criar e configurar worker
        self._current_worker = ScanWorker(
            file_path=str(path),
            audio_model_path=str(AUDIO_MODEL) if AUDIO_MODEL.exists() else "",
            video_model_path=str(VIDEO_MODEL) if VIDEO_MODEL.exists() else "",
        )

        # Conectar sinais do worker
        self._current_worker.progress.connect(self.scan_progress.emit)
        self._current_worker.result.connect(self._on_scan_completed)
        self._current_worker.error.connect(self._on_scan_error)
        self._current_worker.stage_changed.connect(self.scan_stage.emit)
        self._current_worker.log_message.connect(
            lambda msg: logger.info(msg, source="WORKER")
        )

        # Iniciar thread
        self._current_worker.start()

    def cancel_scan(self):
        """Cancela a análise em andamento."""
        if self._current_worker and self._current_worker.isRunning():
            self._current_worker.cancel()
            logger.info("Scan cancelado pelo usuário", source="CONTROLLER")

    def _on_scan_completed(self, result: ScanResult):
        """Callback quando o scan termina com sucesso."""
        # Atualizar histórico
        if self._history:
            self._history[-1].result = result

        logger.info(
            f"Scan finalizado: {Path(result.file_path).name} -> "
            f"{result.verdict.value} ({result.confidence_score:.4f})",
            source="CONTROLLER",
        )

        self.scan_completed.emit(result)

    def _on_scan_error(self, error_message: str):
        """Callback quando o scan falha."""
        logger.error(
            f"Scan falhou: {error_message}", source="CONTROLLER"
        )
        self.scan_error.emit(error_message)

    def get_history(self) -> list[ScanHistoryEntry]:
        """Retorna o histórico de scans da sessão."""
        return list(self._history)

    def get_device_info(self) -> dict[str, str]:
        """Retorna informações do dispositivo de inferência."""
        return self._runtime.get_device_info()

    def get_device_display_name(self) -> str:
        """Retorna nome legível do dispositivo para a UI."""
        return self._runtime.get_provider_display_name()

    def is_scanning(self) -> bool:
        """Verifica se há um scan em andamento."""
        return (
            self._current_worker is not None
            and self._current_worker.isRunning()
        )
