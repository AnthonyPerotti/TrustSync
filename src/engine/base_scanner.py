"""
TrustSync — Base Scanner (Classe Abstrata)

Define a interface padrão que todos os scanners forenses
(áudio, vídeo, documento) devem implementar.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np


class ScanVerdict(Enum):
    """Veredicto da análise forense."""
    AUTHENTIC = "AUTHENTIC"       # Score >= 0.7 — Verde
    INCONCLUSIVE = "INCONCLUSIVE" # 0.4 <= Score < 0.7 — Amarelo
    MANIPULATED = "MANIPULATED"   # Score < 0.4 — Vermelho
    ERROR = "ERROR"               # Falha na análise


@dataclass
class ScanResult:
    """
    Resultado de uma análise forense.

    Attributes:
        file_path: Caminho do arquivo analisado.
        confidence_score: Score de confiança [0.0 - 1.0].
            Quanto maior, mais provável de ser autêntico.
        verdict: Veredicto baseado no confidence_score.
        media_type: Tipo de mídia (audio, video, document).
        features: Features extraídas durante o processamento.
        metadata_findings: Achados da análise de metadados.
        sha256: Hash SHA-256 do arquivo.
        processing_time_ms: Tempo de processamento em milissegundos.
        error_message: Mensagem de erro, se houver.
    """
    file_path: str = ""
    confidence_score: float = 0.0
    verdict: ScanVerdict = ScanVerdict.ERROR
    media_type: str = "unknown"
    features: dict[str, Any] = field(default_factory=dict)
    metadata_findings: list[str] = field(default_factory=list)
    sha256: str = ""
    processing_time_ms: float = 0.0
    error_message: str = ""

    @staticmethod
    def score_to_verdict(score: float) -> ScanVerdict:
        """Converte um score numérico em veredicto."""
        if score >= 0.7:
            return ScanVerdict.AUTHENTIC
        elif score >= 0.4:
            return ScanVerdict.INCONCLUSIVE
        else:
            return ScanVerdict.MANIPULATED

    def to_dict(self) -> dict[str, Any]:
        """Serializa o resultado para dicionário."""
        return {
            "file_path": self.file_path,
            "confidence_score": round(self.confidence_score, 4),
            "verdict": self.verdict.value,
            "media_type": self.media_type,
            "features": self.features,
            "metadata_findings": self.metadata_findings,
            "sha256": self.sha256,
            "processing_time_ms": round(self.processing_time_ms, 2),
            "error_message": self.error_message,
        }


class BaseScanner(ABC):
    """
    Classe abstrata base para todos os scanners forenses.

    Cada scanner deve implementar:
        - scan(): Pipeline completa de análise
        - preprocess(): Pré-processamento do arquivo para inferência
        - postprocess(): Conversão do output do modelo em confidence score
    """

    # Extensões de arquivo suportadas por este scanner
    SUPPORTED_EXTENSIONS: list[str] = []

    @abstractmethod
    def scan(self, file_path: str | Path) -> ScanResult:
        """
        Executa a pipeline completa de análise forense.

        Args:
            file_path: Caminho para o arquivo de mídia.

        Returns:
            ScanResult com o veredicto e detalhes da análise.
        """
        ...

    @abstractmethod
    def preprocess(self, file_path: str | Path) -> np.ndarray:
        """
        Pré-processa o arquivo para formato de entrada do modelo.

        Args:
            file_path: Caminho para o arquivo de mídia.

        Returns:
            Numpy array no formato esperado pelo modelo ONNX.
        """
        ...

    @abstractmethod
    def postprocess(self, output: np.ndarray) -> float:
        """
        Converte a saída do modelo em um confidence score.

        Args:
            output: Output raw do modelo ONNX.

        Returns:
            Confidence score entre 0.0 (manipulado) e 1.0 (autêntico).
        """
        ...

    def supports_file(self, file_path: str | Path) -> bool:
        """Verifica se este scanner suporta o tipo de arquivo."""
        ext = Path(file_path).suffix.lower()
        return ext in self.SUPPORTED_EXTENSIONS
