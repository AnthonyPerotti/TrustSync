"""
TrustSync — Scan Worker (QThread)

Worker thread para executar análises forenses sem bloquear a UI.
Emite sinais Qt com progresso, resultado, logs e erros.
"""

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from src.engine.audio_scanner import AudioScanner
from src.engine.base_scanner import ScanResult, ScanVerdict
from src.engine.document_scanner import DocumentScanner
from src.engine.video_scanner import VideoScanner
from src.utils.logger import ForensicLogger

logger = ForensicLogger()


class ScanWorker(QThread):
    """
    Worker thread que executa a pipeline de análise forense.

    Sinais emitidos:
        - progress(int): Percentual de progresso (0-100)
        - result(object): ScanResult com o resultado da análise
        - error(str): Mensagem de erro em caso de falha
        - log_message(str): Mensagens de log durante o processamento
        - stage_changed(str): Nome da etapa atual do pipeline
    """

    progress = Signal(int)
    result = Signal(object)
    error = Signal(str)
    log_message = Signal(str)
    stage_changed = Signal(str)

    def __init__(
        self,
        file_path: str,
        audio_model_path: str = "",
        video_model_path: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self._file_path = Path(file_path)
        self._audio_model_path = audio_model_path or None
        self._video_model_path = video_model_path or None
        self._is_cancelled = False

    def cancel(self):
        """Solicita cancelamento da análise em andamento."""
        self._is_cancelled = True
        logger.info("Cancelamento solicitado", source="WORKER")

    def run(self):
        """Executa a pipeline de análise na thread separada."""
        try:
            if self._is_cancelled:
                return

            file_path = self._file_path

            if not file_path.exists():
                self.error.emit(f"Arquivo não encontrado: {file_path}")
                return

            # Determinar tipo de mídia
            self.stage_changed.emit("Detectando tipo de mídia...")
            self.progress.emit(5)

            scanner = self._resolve_scanner(file_path)

            if scanner is None:
                self.error.emit(
                    f"Tipo de arquivo não suportado: {file_path.suffix}"
                )
                return

            if self._is_cancelled:
                return

            # Executar scan
            self.stage_changed.emit("Analisando arquivo...")
            self.progress.emit(20)

            scan_result = scanner.scan(file_path)

            if self._is_cancelled:
                return

            self.progress.emit(100)
            self.stage_changed.emit("Concluído")
            self.result.emit(scan_result)

        except Exception as e:
            logger.error(f"Erro no worker: {e}", source="WORKER")
            self.error.emit(str(e))

    def _resolve_scanner(self, file_path: Path):
        """Seleciona o scanner adequado com base na extensão do arquivo."""
        audio_scanner = AudioScanner(model_path=self._audio_model_path)
        video_scanner = VideoScanner(model_path=self._video_model_path)
        doc_scanner = DocumentScanner()

        scanners = [audio_scanner, video_scanner, doc_scanner]

        for scanner in scanners:
            if scanner.supports_file(file_path):
                scanner_name = scanner.__class__.__name__
                self.log_message.emit(
                    f"Scanner selecionado: {scanner_name}"
                )
                logger.info(
                    f"Scanner resolvido: {scanner_name} para "
                    f"'{file_path.name}'",
                    source="WORKER",
                )
                return scanner

        return None
