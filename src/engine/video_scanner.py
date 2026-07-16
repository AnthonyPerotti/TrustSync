"""
TrustSync — Video Scanner

Análise forense de vídeo para detecção de deepfakes visuais.
Extrai frames-chave com OpenCV, pré-processa para MobileNetV3
e executa inferência ONNX com agregação de scores.
"""

import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from src.engine.base_scanner import BaseScanner, ScanResult, ScanVerdict
from src.engine.runtime_manager import RuntimeManager
from src.utils.file_hash import compute_sha256
from src.utils.logger import ForensicLogger
from src.utils.metadata_extractor import MetadataExtractor

logger = ForensicLogger()

# ─── Constantes ───────────────────────────────────────────────

INPUT_SIZE = (224, 224)        # MobileNetV3 input size
MAX_FRAMES = 16                # Frames-chave para análise
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


class VideoScanner(BaseScanner):
    """
    Scanner forense para detecção de deepfake em vídeos.

    Extrai frames-chave uniformemente distribuídos, pré-processa
    para MobileNetV3 (224×224, normalização ImageNet) e agrega
    scores de múltiplos frames para o veredicto final.
    """

    SUPPORTED_EXTENSIONS = [
        ".mp4", ".avi", ".mkv", ".mov", ".wmv",
        ".flv", ".webm", ".m4v", ".mpeg", ".mpg",
    ]

    def __init__(
        self,
        model_path: Optional[str | Path] = None,
        max_frames: int = MAX_FRAMES,
    ):
        self._model_path = Path(model_path) if model_path else None
        self._max_frames = max_frames
        self._runtime = RuntimeManager()
        self._metadata_extractor = MetadataExtractor()

    def scan(self, file_path: str | Path) -> ScanResult:
        """Executa pipeline forense completa de vídeo."""
        file_path = Path(file_path)
        start_time = time.perf_counter()

        logger.info(
            f"Iniciando análise de vídeo: {file_path.name}",
            source="VIDEO_SCANNER",
        )

        result = ScanResult(file_path=str(file_path), media_type="video")

        try:
            # Hash de integridade
            result.sha256 = compute_sha256(file_path)

            # Metadados
            metadata = self._metadata_extractor.extract(file_path)
            if metadata:
                suspicion = self._metadata_extractor.analyze_suspicion(metadata)
                result.metadata_findings = suspicion["findings"]

            # Extrair frames-chave
            frames = self._extract_key_frames(file_path)
            result.features["num_frames_extracted"] = len(frames)

            if len(frames) == 0:
                raise ValueError("Nenhum frame pôde ser extraído do vídeo")

            # Inferência
            if self._model_path and self._model_path.exists():
                scores = []
                session = self._runtime.load_model(self._model_path)

                # Detectar resolução exata do modelo (ex: 384x384 para Vision Transformer ou 224x224)
                target_size = INPUT_SIZE
                try:
                    shape = session.get_inputs()[0].shape
                    if len(shape) >= 4 and isinstance(shape[2], int) and isinstance(shape[3], int) and shape[2] > 0 and shape[3] > 0:
                        target_size = (shape[3], shape[2])
                    else:
                        # Se simbólico, checamos se o modelo é um Vision Transformer com 577 tokens
                        for node in session.get_inputs():
                            if "pixel_values" in node.name:
                                target_size = (384, 384)
                except Exception:
                    pass

                for i, frame in enumerate(frames):
                    input_tensor = self._preprocess_frame(frame, target_size=target_size)
                    raw_output = self._runtime.run_inference(
                        session, input_tensor
                    )
                    score = self.postprocess(raw_output)
                    scores.append(score)

                # Agregar scores: média ponderada (frames centrais pesam mais)
                confidence = self._aggregate_scores(scores)
                result.features["per_frame_scores"] = [
                    round(s, 4) for s in scores
                ]
            else:
                confidence = 0.80  # Heurística sem modelo
                logger.info(
                    "Modelo ONNX não disponível — score heurístico",
                    source="VIDEO_SCANNER",
                )

            result.confidence_score = confidence
            result.verdict = ScanResult.score_to_verdict(confidence)

            elapsed = (time.perf_counter() - start_time) * 1000
            result.processing_time_ms = elapsed

            logger.info(
                f"Análise concluída: {file_path.name} -> "
                f"Score: {confidence:.4f} | "
                f"Veredicto: {result.verdict.value} | "
                f"Frames: {len(frames)} | Tempo: {elapsed:.0f}ms",
                source="VIDEO_SCANNER",
            )

            return result

        except Exception as e:
            elapsed = (time.perf_counter() - start_time) * 1000
            result.processing_time_ms = elapsed
            result.verdict = ScanVerdict.ERROR
            result.error_message = str(e)
            logger.error(
                f"Falha na análise de '{file_path.name}': {e}",
                source="VIDEO_SCANNER",
            )
            return result

    def preprocess(self, file_path: str | Path) -> np.ndarray:
        """Pré-processa o primeiro frame do vídeo."""
        frames = self._extract_key_frames(file_path, max_frames=1)
        if not frames:
            raise ValueError("Não foi possível extrair frames")
        target_size = INPUT_SIZE
        if self._model_path and self._model_path.exists():
            try:
                session = self._runtime.load_model(self._model_path)
                shape = session.get_inputs()[0].shape
                if len(shape) >= 4 and isinstance(shape[2], int) and isinstance(shape[3], int) and shape[2] > 0 and shape[3] > 0:
                    target_size = (shape[3], shape[2])
                else:
                    for node in session.get_inputs():
                        if "pixel_values" in node.name:
                            target_size = (384, 384)
            except Exception:
                pass
        return self._preprocess_frame(frames[0], target_size=target_size)

    def postprocess(self, output: np.ndarray) -> float:
        """Converte output do modelo em confidence score."""
        if output.ndim > 1:
            output = output[0]

        exp_values = np.exp(output - np.max(output))
        probabilities = exp_values / exp_values.sum()

        if len(probabilities) >= 2:
            confidence = float(probabilities[0])
        else:
            confidence = float(probabilities[0])

        return float(np.clip(confidence, 0.0, 1.0))

    def _extract_key_frames(
        self, file_path: str | Path, max_frames: Optional[int] = None
    ) -> list[np.ndarray]:
        """
        Extrai frames-chave uniformemente distribuídos do vídeo.

        Args:
            file_path: Caminho para o arquivo de vídeo.
            max_frames: Número máximo de frames a extrair.

        Returns:
            Lista de frames como numpy arrays (BGR).
        """
        max_frames = max_frames or self._max_frames
        cap = cv2.VideoCapture(str(file_path))

        if not cap.isOpened():
            logger.error(
                f"Não foi possível abrir: {file_path}", source="VIDEO_SCANNER"
            )
            return []

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)

        if total_frames <= 0:
            cap.release()
            return []

        # Indices uniformemente distribuídos
        indices = np.linspace(
            0, total_frames - 1, min(max_frames, total_frames), dtype=int
        )

        frames = []
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret:
                frames.append(frame)

        cap.release()

        logger.debug(
            f"Extraídos {len(frames)}/{total_frames} frames "
            f"({fps:.1f} FPS)",
            source="VIDEO_SCANNER",
        )

        return frames

    def _preprocess_frame(self, frame: np.ndarray, target_size: tuple[int, int] = INPUT_SIZE) -> np.ndarray:
        """
        Pré-processa um frame para entrada do modelo (MobileNetV3 ou Vision Transformer).

        Resize → target_size (ex: 224×224 ou 384×384), BGR→RGB, normalização ImageNet, NCHW.
        """
        # Resize
        resized = cv2.resize(frame, target_size, interpolation=cv2.INTER_LINEAR)

        # BGR → RGB e normalizar para [0, 1]
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0

        # Normalização ImageNet
        rgb = (rgb - IMAGENET_MEAN) / IMAGENET_STD

        # HWC → NCHW (batch=1)
        tensor = np.transpose(rgb, (2, 0, 1))
        tensor = np.expand_dims(tensor, axis=0).astype(np.float32)

        return tensor

    def _aggregate_scores(self, scores: list[float]) -> float:
        """
        Agrega scores de múltiplos frames.

        Usa média ponderada onde frames centrais têm peso maior
        (deepfakes costumam ser mais evidentes no meio do vídeo).
        """
        n = len(scores)
        if n == 0:
            return 0.0
        if n == 1:
            return scores[0]

        # Pesos gaussianos centralizados
        weights = np.exp(-0.5 * ((np.arange(n) - n / 2) / (n / 4)) ** 2)
        weights /= weights.sum()

        return float(np.dot(scores, weights))
