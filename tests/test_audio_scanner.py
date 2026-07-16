"""
TrustSync — Testes do Audio Scanner

Testes unitários para a classe AudioScanner,
verificando pré-processamento, extração de features
e pipeline completa de análise.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Adicionar root do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.engine.audio_scanner import AudioScanner, TARGET_SAMPLE_RATE
from src.engine.base_scanner import ScanResult, ScanVerdict


class TestAudioScannerInit:
    """Testes de inicialização do AudioScanner."""

    def test_init_without_model(self):
        """Scanner deve inicializar sem modelo ONNX."""
        scanner = AudioScanner()
        assert scanner._model_path is None
        assert scanner._sample_rate == TARGET_SAMPLE_RATE

    def test_init_with_model_path(self):
        """Scanner deve aceitar caminho de modelo."""
        scanner = AudioScanner(model_path="models/test.onnx")
        assert scanner._model_path == Path("models/test.onnx")

    def test_supported_extensions(self):
        """Scanner deve suportar formatos de áudio comuns."""
        scanner = AudioScanner()
        assert scanner.supports_file("test.wav")
        assert scanner.supports_file("test.mp3")
        assert scanner.supports_file("test.flac")
        assert scanner.supports_file("test.ogg")
        assert not scanner.supports_file("test.mp4")
        assert not scanner.supports_file("test.png")
        assert not scanner.supports_file("test.pdf")


class TestAudioScannerPreprocess:
    """Testes de pré-processamento de áudio."""

    @patch("src.engine.audio_scanner.librosa")
    def test_preprocess_shape(self, mock_librosa):
        """Output do preprocess deve ter shape (1, num_samples)."""
        # Mock librosa.load para retornar waveform sintético
        fake_waveform = np.random.randn(16000 * 5).astype(np.float32)
        mock_librosa.load.return_value = (fake_waveform, 16000)

        scanner = AudioScanner(max_duration=5.0)
        result = scanner.preprocess("fake_audio.wav")

        assert result.ndim == 2
        assert result.shape[0] == 1  # Batch dimension
        assert result.shape[1] == int(16000 * 5.0)  # Samples

    @patch("src.engine.audio_scanner.librosa")
    def test_preprocess_dtype(self, mock_librosa):
        """Output deve ser float32."""
        fake_waveform = np.random.randn(16000).astype(np.float32)
        mock_librosa.load.return_value = (fake_waveform, 16000)

        scanner = AudioScanner(max_duration=1.0)
        result = scanner.preprocess("fake_audio.wav")

        assert result.dtype == np.float32

    @patch("src.engine.audio_scanner.librosa")
    def test_preprocess_normalization(self, mock_librosa):
        """Waveform deve ser normalizado para [-1, 1]."""
        fake_waveform = np.array([0.5, -0.3, 1.0, -0.8], dtype=np.float32)
        mock_librosa.load.return_value = (fake_waveform, 16000)

        scanner = AudioScanner(max_duration=30.0)
        result = scanner.preprocess("fake_audio.wav")

        assert np.max(np.abs(result)) <= 1.0 + 1e-6

    @patch("src.engine.audio_scanner.librosa")
    def test_preprocess_padding(self, mock_librosa):
        """Áudio curto deve ser padded com zeros."""
        # 1 segundo de áudio, mas max_duration é 5s
        short_waveform = np.random.randn(16000).astype(np.float32)
        mock_librosa.load.return_value = (short_waveform, 16000)

        scanner = AudioScanner(max_duration=5.0)
        result = scanner.preprocess("short_audio.wav")

        expected_length = int(16000 * 5.0)
        assert result.shape[1] == expected_length


class TestAudioScannerPostprocess:
    """Testes de pós-processamento."""

    def test_postprocess_softmax(self):
        """Postprocess deve aplicar softmax e retornar score [0, 1]."""
        scanner = AudioScanner()

        # Simular output do modelo: [logit_autêntico, logit_manipulado]
        fake_output = np.array([[2.0, -1.0]], dtype=np.float32)
        score = scanner.postprocess(fake_output)

        assert 0.0 <= score <= 1.0
        assert score > 0.5  # logit autêntico > manipulado

    def test_postprocess_manipulated(self):
        """Score baixo quando logit de manipulação é alto."""
        scanner = AudioScanner()

        fake_output = np.array([[-2.0, 3.0]], dtype=np.float32)
        score = scanner.postprocess(fake_output)

        assert score < 0.5  # Manipulado


class TestScanResult:
    """Testes do dataclass ScanResult."""

    def test_score_to_verdict_authentic(self):
        assert ScanResult.score_to_verdict(0.85) == ScanVerdict.AUTHENTIC
        assert ScanResult.score_to_verdict(0.70) == ScanVerdict.AUTHENTIC

    def test_score_to_verdict_inconclusive(self):
        assert ScanResult.score_to_verdict(0.55) == ScanVerdict.INCONCLUSIVE
        assert ScanResult.score_to_verdict(0.40) == ScanVerdict.INCONCLUSIVE

    def test_score_to_verdict_manipulated(self):
        assert ScanResult.score_to_verdict(0.30) == ScanVerdict.MANIPULATED
        assert ScanResult.score_to_verdict(0.0) == ScanVerdict.MANIPULATED

    def test_to_dict(self):
        result = ScanResult(
            file_path="test.wav",
            confidence_score=0.85,
            verdict=ScanVerdict.AUTHENTIC,
            media_type="audio",
        )
        d = result.to_dict()
        assert d["confidence_score"] == 0.85
        assert d["verdict"] == "AUTHENTIC"
        assert d["media_type"] == "audio"
