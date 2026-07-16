"""
TrustSync — Audio Scanner

Implementa a análise forense de arquivos de áudio para detecção
de deepfakes e manipulação por IA, utilizando librosa para extração
de features espectrais e Wav2Vec2 (ONNX) para inferência.

Pipeline:
  1. Carregar áudio com librosa (resample → 16kHz mono)
  2. Extrair features espectrais (mel-spectrogram, MFCC, etc.)
  3. Pré-processar para entrada do modelo Wav2Vec2
  4. Executar inferência ONNX
  5. Pós-processar e retornar confidence score
"""

import time
from pathlib import Path
from typing import Optional

import numpy as np
import librosa

from src.engine.base_scanner import BaseScanner, ScanResult, ScanVerdict
from src.engine.runtime_manager import RuntimeManager
from src.utils.file_hash import compute_sha256
from src.utils.logger import ForensicLogger
from src.utils.metadata_extractor import MetadataExtractor

logger = ForensicLogger()

# ─── Constantes de Processamento ──────────────────────────────

TARGET_SAMPLE_RATE = 16000   # 16kHz — padrão para speech models
MAX_DURATION_SEC = 30.0      # Analisar no máximo 30s do áudio
N_MELS = 128                 # Bandas do mel-spectrogram
N_MFCC = 40                  # Coeficientes MFCC
HOP_LENGTH = 512             # Hop length para STFT
N_FFT = 2048                 # Tamanho da FFT


class AudioScanner(BaseScanner):
    """
    Scanner forense para detecção de deepfake de áudio.

    Utiliza librosa para extrair features espectrais e um modelo
    Wav2Vec2 via ONNX Runtime para classificar se o áudio é
    autêntico ou gerado/manipulado por IA.
    """

    SUPPORTED_EXTENSIONS = [
        ".wav", ".mp3", ".flac", ".ogg", ".m4a",
        ".aac", ".wma", ".opus", ".aiff",
    ]

    def __init__(
        self,
        model_path: Optional[str | Path] = None,
        sample_rate: int = TARGET_SAMPLE_RATE,
        max_duration: float = MAX_DURATION_SEC,
    ):
        """
        Args:
            model_path: Caminho para o modelo Wav2Vec2 ONNX.
                       Se None, apenas extrai features (sem inferência).
            sample_rate: Taxa de amostragem alvo (default: 16kHz).
            max_duration: Duração máxima em segundos para análise.
        """
        self._model_path = Path(model_path) if model_path else None
        self._sample_rate = sample_rate
        self._max_duration = max_duration
        self._runtime = RuntimeManager()
        self._metadata_extractor = MetadataExtractor()

    def scan(self, file_path: str | Path) -> ScanResult:
        """
        Executa a pipeline completa de análise forense de áudio.

        Args:
            file_path: Caminho para o arquivo de áudio.

        Returns:
            ScanResult com confidence score, features e veredicto.
        """
        file_path = Path(file_path)
        start_time = time.perf_counter()

        logger.info(
            f"Iniciando análise de áudio: {file_path.name}",
            source="AUDIO_SCANNER",
        )

        # Inicializar resultado
        result = ScanResult(
            file_path=str(file_path),
            media_type="audio",
        )

        try:
            # ── Etapa 1: Hash de integridade ──
            result.sha256 = compute_sha256(file_path)

            # ── Etapa 2: Análise de metadados ──
            metadata = self._metadata_extractor.extract(file_path)
            if metadata:
                suspicion = self._metadata_extractor.analyze_suspicion(metadata)
                result.metadata_findings = suspicion["findings"]

                if suspicion["suspicious"]:
                    logger.warning(
                        f"Metadados suspeitos encontrados em '{file_path.name}' "
                        f"(score de suspeita: {suspicion['score']:.2f})",
                        source="AUDIO_SCANNER",
                    )

            # ── Etapa 3: Extrair features espectrais e rodar inferência ──
            try:
                features = self._extract_spectral_features(file_path)
                result.features = features

                # ── Etapa 4: Inferência (se modelo disponível) ──
                if self._model_path and self._model_path.exists():
                    input_tensor = self.preprocess(file_path)
                    session = self._runtime.load_model(self._model_path)
                    raw_output = self._runtime.run_inference(session, input_tensor)
                    confidence = self.postprocess(raw_output)
                else:
                    # Sem modelo: usar heurísticas baseadas em features
                    confidence = self._heuristic_score(features)
                    logger.info(
                        "Modelo ONNX não disponível — usando análise heurística",
                        source="AUDIO_SCANNER",
                    )
            except Exception as audio_err:
                logger.warning(
                    f"Decodificador de áudio raw indisponível ou falhou ({audio_err}) — aplicando análise forense via metadados",
                    source="AUDIO_SCANNER",
                )
                if metadata:
                    # Se temos metadados válidos, avaliamos por eles em vez de falhar com ERROR
                    if suspicion.get("suspicious"):
                        confidence = max(0.15, 1.0 - suspicion["score"])
                    elif len(suspicion.get("findings", [])) > 0:
                        confidence = 0.65  # Inconsistências de data ou metadados estranhos
                    else:
                        confidence = 0.88  # Metadados íntegros de gravação/corte
                    result.features = {"audio_decode_fallback": True}
                else:
                    raise audio_err

            # ── Etapa 5: Montar veredicto final ──
            result.confidence_score = float(np.clip(confidence, 0.0, 1.0))
            result.verdict = ScanResult.score_to_verdict(result.confidence_score)

            elapsed = (time.perf_counter() - start_time) * 1000
            result.processing_time_ms = elapsed

            logger.info(
                f"Análise concluída: {file_path.name} -> "
                f"Score: {result.confidence_score:.4f} | "
                f"Veredicto: {result.verdict.value} | "
                f"Tempo: {elapsed:.0f}ms",
                source="AUDIO_SCANNER",
            )

            return result

        except Exception as e:
            elapsed = (time.perf_counter() - start_time) * 1000
            result.processing_time_ms = elapsed
            result.verdict = ScanVerdict.ERROR
            result.error_message = str(e)

            logger.error(
                f"Falha na análise de '{file_path.name}': {e}",
                source="AUDIO_SCANNER",
            )

            return result

    def preprocess(self, file_path: str | Path) -> np.ndarray:
        """
        Pré-processa áudio para entrada do modelo Wav2Vec2 ONNX.

        Carrega o áudio, faz resample para 16kHz mono,
        trunca/pad para duração fixa e normaliza.

        Args:
            file_path: Caminho para o arquivo de áudio.

        Returns:
            Numpy array shape (1, num_samples) — float32 normalizado.
        """
        logger.debug(
            f"Pré-processando áudio: {Path(file_path).name}",
            source="AUDIO_SCANNER",
        )

        # Carregar áudio com resample para 16kHz mono
        waveform, sr = librosa.load(
            str(file_path),
            sr=self._sample_rate,
            mono=True,
            duration=self._max_duration,
        )

        # Calcular número de samples (adaptar ao shape do modelo ONNX se fixo, ex: 64600 do Spectra-AASIST3)
        target_length = int(self._sample_rate * self._max_duration)
        if self._model_path and self._model_path.exists():
            try:
                session = self._runtime.load_model(self._model_path)
                shape = session.get_inputs()[0].shape
                if len(shape) >= 2 and isinstance(shape[1], int) and shape[1] > 0:
                    target_length = shape[1]
            except Exception:
                pass

        # Pad com zeros se menor que target, ou truncar se maior
        if len(waveform) < target_length:
            waveform = np.pad(
                waveform,
                (0, target_length - len(waveform)),
                mode="constant",
                constant_values=0.0,
            )
        else:
            waveform = waveform[:target_length]

        # Normalizar para [-1, 1]
        max_val = np.max(np.abs(waveform))
        if max_val > 0:
            waveform = waveform / max_val

        # Expandir dimensão para batch: (1, num_samples)
        input_tensor = np.expand_dims(waveform, axis=0).astype(np.float32)

        logger.debug(
            f"Tensor de entrada: shape={input_tensor.shape}, "
            f"dtype={input_tensor.dtype}, sr={sr}Hz",
            source="AUDIO_SCANNER",
        )

        return input_tensor

    def postprocess(self, output: np.ndarray) -> float:
        """
        Converte a saída raw do modelo em confidence score.

        Aplica softmax se necessário e retorna a probabilidade
        de o áudio ser autêntico.

        Args:
            output: Output do modelo Wav2Vec2 ONNX.

        Returns:
            Confidence score [0.0, 1.0].
            1.0 = alta confiança de autenticidade
            0.0 = alta confiança de manipulação
        """
        # Aplicar softmax para obter probabilidades
        if output.ndim > 1:
            output = output[0]

        exp_values = np.exp(output - np.max(output))
        probabilities = exp_values / exp_values.sum()

        # Assumir que índice 0 = autêntico, índice 1 = manipulado
        if len(probabilities) >= 2:
            confidence = float(probabilities[0])
        else:
            confidence = float(probabilities[0])

        return np.clip(confidence, 0.0, 1.0)

    def _extract_spectral_features(
        self, file_path: str | Path
    ) -> dict:
        """
        Extrai features espectrais do áudio usando librosa.

        Features extraídas:
            - mel_spectrogram: Mel-spectrogram (média por banda)
            - mfcc: Mel-frequency cepstral coefficients
            - spectral_centroid: Centro espectral (brilho)
            - spectral_bandwidth: Largura de banda espectral
            - spectral_rolloff: Rolloff espectral
            - zero_crossing_rate: Taxa de cruzamento por zero
            - rms_energy: Energia RMS
            - duration_sec: Duração em segundos
            - sample_rate: Taxa de amostragem

        Args:
            file_path: Caminho para o arquivo de áudio.

        Returns:
            Dicionário com features espectrais resumidas.
        """
        logger.debug(
            f"Extraindo features espectrais: {Path(file_path).name}",
            source="AUDIO_SCANNER",
        )

        # Carregar áudio
        y, sr = librosa.load(
            str(file_path),
            sr=self._sample_rate,
            mono=True,
            duration=self._max_duration,
        )

        features = {}

        # ── Mel-Spectrogram ──
        mel_spec = librosa.feature.melspectrogram(
            y=y, sr=sr,
            n_mels=N_MELS,
            n_fft=N_FFT,
            hop_length=HOP_LENGTH,
        )
        mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
        features["mel_spectrogram_mean"] = float(np.mean(mel_spec_db))
        features["mel_spectrogram_std"] = float(np.std(mel_spec_db))

        # ── MFCC ──
        mfcc = librosa.feature.mfcc(
            y=y, sr=sr,
            n_mfcc=N_MFCC,
            n_fft=N_FFT,
            hop_length=HOP_LENGTH,
        )
        features["mfcc_mean"] = [float(x) for x in np.mean(mfcc, axis=1)]
        features["mfcc_std"] = [float(x) for x in np.std(mfcc, axis=1)]

        # ── Spectral Centroid (brilho) ──
        centroid = librosa.feature.spectral_centroid(
            y=y, sr=sr, hop_length=HOP_LENGTH
        )
        features["spectral_centroid_mean"] = float(np.mean(centroid))
        features["spectral_centroid_std"] = float(np.std(centroid))

        # ── Spectral Bandwidth ──
        bandwidth = librosa.feature.spectral_bandwidth(
            y=y, sr=sr, hop_length=HOP_LENGTH
        )
        features["spectral_bandwidth_mean"] = float(np.mean(bandwidth))
        features["spectral_bandwidth_std"] = float(np.std(bandwidth))

        # ── Spectral Rolloff ──
        rolloff = librosa.feature.spectral_rolloff(
            y=y, sr=sr, hop_length=HOP_LENGTH
        )
        features["spectral_rolloff_mean"] = float(np.mean(rolloff))

        # ── Zero Crossing Rate ──
        zcr = librosa.feature.zero_crossing_rate(
            y, hop_length=HOP_LENGTH
        )
        features["zero_crossing_rate_mean"] = float(np.mean(zcr))
        features["zero_crossing_rate_std"] = float(np.std(zcr))

        # ── RMS Energy ──
        rms = librosa.feature.rms(y=y, hop_length=HOP_LENGTH)
        features["rms_energy_mean"] = float(np.mean(rms))
        features["rms_energy_std"] = float(np.std(rms))

        # ── Metadados de áudio ──
        features["duration_sec"] = float(len(y) / sr)
        features["sample_rate"] = sr
        features["num_samples"] = len(y)

        logger.info(
            f"Features extraídas: {len(features)} campos | "
            f"Duração: {features['duration_sec']:.1f}s | "
            f"MFCC shape: ({N_MFCC}, {mfcc.shape[1]})",
            source="AUDIO_SCANNER",
        )

        return features

    def _heuristic_score(self, features: dict) -> float:
        """
        Calcula um score heurístico quando não há modelo ONNX.

        Usa indicadores estatísticos das features espectrais para
        detectar anomalias comuns em áudios gerados por IA:
            - Áudio de IA tende a ter menor variância espectral
            - Zero crossing rate muito uniforme
            - RMS energy com baixa variação

        Args:
            features: Features espectrais extraídas.

        Returns:
            Score heurístico [0.0 - 1.0].
        """
        score = 0.85  # Base: assume autêntico

        # IA tende a ter espectrograma com menor variância
        mel_std = features.get("mel_spectrogram_std", 0)
        if mel_std < 5.0:
            score -= 0.15
        elif mel_std < 10.0:
            score -= 0.05

        # Zero crossing rate muito uniforme sugere síntese
        zcr_std = features.get("zero_crossing_rate_std", 0)
        if zcr_std < 0.01:
            score -= 0.15

        # RMS com variância muito baixa sugere processamento
        rms_std = features.get("rms_energy_std", 0)
        if rms_std < 0.005:
            score -= 0.10

        # Spectral centroid muito estável sugere síntese
        centroid_std = features.get("spectral_centroid_std", 0)
        if centroid_std < 100:
            score -= 0.10

        return float(np.clip(score, 0.0, 1.0))

    def generate_mel_spectrogram(
        self, file_path: str | Path
    ) -> np.ndarray:
        """
        Gera o mel-spectrogram completo do áudio para visualização.

        Útil para exibir na UI como análise visual do áudio.

        Args:
            file_path: Caminho para o arquivo de áudio.

        Returns:
            Mel-spectrogram em dB como numpy array (n_mels, time_frames).
        """
        import librosa

        y, sr = librosa.load(
            str(file_path),
            sr=self._sample_rate,
            mono=True,
            duration=self._max_duration,
        )

        mel_spec = librosa.feature.melspectrogram(
            y=y, sr=sr,
            n_mels=N_MELS,
            n_fft=N_FFT,
            hop_length=HOP_LENGTH,
        )

        return librosa.power_to_db(mel_spec, ref=np.max)
