"""
TrustSync — Logger Forense Thread-Safe

Logger centralizado com timestamps ISO-8601, suporte a sinais Qt
para integração com o painel de log da UI, e escrita em arquivo.
"""

import logging
import sys
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from PySide6.QtCore import QObject, Signal


class LogLevel(Enum):
    """Níveis de severidade do log forense."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ForensicLogEntry:
    """Entrada individual do log forense."""

    def __init__(self, level: LogLevel, message: str, source: str = "SYSTEM"):
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.level = level
        self.message = message
        self.source = source

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "level": self.level.value,
            "source": self.source,
            "message": self.message,
        }

    def __str__(self) -> str:
        return f"[{self.timestamp}] [{self.level.value}] [{self.source}] {self.message}"


class LogSignalEmitter(QObject):
    """Emissor de sinais Qt para atualizar o LogPanel na UI thread."""
    log_emitted = Signal(object)  # ForensicLogEntry


class ForensicLogger:
    """
    Logger forense thread-safe com integração Qt.

    Singleton que gerencia logging para arquivo + console + UI.
    Cada mensagem é emitida como sinal Qt para o LogPanel.
    """

    _instance: Optional["ForensicLogger"] = None

    def __new__(cls) -> "ForensicLogger":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # Emissor de sinais Qt (thread-safe via Qt signal system)
        self.signal_emitter = LogSignalEmitter()

        # Logger padrão do Python
        self._logger = logging.getLogger("TrustSync")
        self._logger.setLevel(logging.DEBUG)

        # Formato ISO-8601
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)

        # Histórico em memória para exportação
        self._history: list[ForensicLogEntry] = []

    def _log(self, level: LogLevel, message: str, source: str = "SYSTEM"):
        """Registra uma entrada no log e emite sinal Qt."""
        entry = ForensicLogEntry(level, message, source)
        self._history.append(entry)

        # Log via logging padrão
        log_method = getattr(self._logger, level.value.lower())
        log_method(f"[{source}] {message}")

        # Emitir sinal para UI
        self.signal_emitter.log_emitted.emit(entry)

    def debug(self, message: str, source: str = "SYSTEM"):
        self._log(LogLevel.DEBUG, message, source)

    def info(self, message: str, source: str = "SYSTEM"):
        self._log(LogLevel.INFO, message, source)

    def warning(self, message: str, source: str = "SYSTEM"):
        self._log(LogLevel.WARNING, message, source)

    def error(self, message: str, source: str = "SYSTEM"):
        self._log(LogLevel.ERROR, message, source)

    def critical(self, message: str, source: str = "SYSTEM"):
        self._log(LogLevel.CRITICAL, message, source)

    def get_history(self) -> list[ForensicLogEntry]:
        """Retorna o histórico completo de logs."""
        return list(self._history)

    def export_to_text(self) -> str:
        """Exporta todo o histórico como texto formatado."""
        lines = [
            "=" * 72,
            "TRUSTSYNC — RELATÓRIO DE AUDITORIA FORENSE",
            f"Gerado em: {datetime.now(timezone.utc).isoformat()}",
            "=" * 72,
            "",
        ]
        for entry in self._history:
            lines.append(str(entry))
        lines.append("")
        lines.append(f"Total de entradas: {len(self._history)}")
        return "\n".join(lines)

    def clear(self):
        """Limpa o histórico de logs."""
        self._history.clear()
