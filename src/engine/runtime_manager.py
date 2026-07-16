"""
TrustSync — Runtime Manager

Gerencia a detecção de hardware (GPU/CPU) e inicialização do
motor de inferência ONNX Runtime com fallback para OpenVINO.

Hierarquia de providers:
  1. CUDAExecutionProvider (NVIDIA GPU + CUDA)
  2. DmlExecutionProvider  (DirectML — AMD/Intel/NVIDIA no Windows)
  3. OpenVINOExecutionProvider (CPU otimizada Intel)
  4. CPUExecutionProvider  (fallback universal)
"""

from pathlib import Path
from typing import Any, Optional

import numpy as np

from src.utils.logger import ForensicLogger

logger = ForensicLogger()


class RuntimeManager:
    """
    Singleton que gerencia sessões de inferência ONNX Runtime.

    Detecta automaticamente o melhor provider disponível e
    fornece uma API unificada para carregar e executar modelos.
    """

    _instance: Optional["RuntimeManager"] = None

    def __new__(cls) -> "RuntimeManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._provider: str = "CPUExecutionProvider"
        self._sessions: dict[str, Any] = {}
        self._device_info: dict[str, str] = {}

        self._detect_provider()

    def _detect_provider(self):
        """Detecta o melhor provider de execução disponível."""
        # Tentar ONNX Runtime primeiro
        try:
            import onnxruntime as ort

            available = ort.get_available_providers()
            logger.info(
                f"ONNX Runtime v{ort.__version__} — "
                f"Providers disponíveis: {available}",
                source="RUNTIME",
            )

            # Ordem de preferência
            preferred = [
                "CUDAExecutionProvider",
                "DmlExecutionProvider",
                "OpenVINOExecutionProvider",
                "CPUExecutionProvider",
            ]

            for provider in preferred:
                if provider in available:
                    self._provider = provider
                    break

            self._device_info = {
                "engine": "ONNX Runtime",
                "version": ort.__version__,
                "provider": self._provider,
                "providers_available": ", ".join(available),
            }

        except ImportError:
            logger.warning(
                "ONNX Runtime não encontrado, tentando OpenVINO...",
                source="RUNTIME",
            )
            self._try_openvino_fallback()
            return

        # Se apenas CPU, tentar OpenVINO como otimização
        if self._provider == "CPUExecutionProvider":
            self._try_openvino_fallback()

        logger.info(
            f"Provider selecionado: {self._provider}",
            source="RUNTIME",
        )

    def _try_openvino_fallback(self):
        """Tenta usar OpenVINO como fallback otimizado para CPU."""
        try:
            import openvino as ov

            self._provider = "OpenVINOExecutionProvider"
            self._device_info = {
                "engine": "OpenVINO",
                "version": ov.__version__,
                "provider": "OpenVINOExecutionProvider",
                "providers_available": "OpenVINOExecutionProvider",
            }
            logger.info(
                f"OpenVINO v{ov.__version__} disponível como fallback CPU",
                source="RUNTIME",
            )
        except ImportError:
            self._provider = "CPUExecutionProvider"
            self._device_info = {
                "engine": "ONNX Runtime (CPU)",
                "version": "N/A",
                "provider": "CPUExecutionProvider",
                "providers_available": "CPUExecutionProvider",
            }
            logger.warning(
                "Nenhuma aceleração disponível — usando CPU pura",
                source="RUNTIME",
            )

    def load_model(self, model_path: str | Path) -> Any:
        """
        Carrega um modelo ONNX e retorna a sessão de inferência.

        Args:
            model_path: Caminho para o arquivo .onnx.

        Returns:
            InferenceSession do ONNX Runtime.

        Raises:
            FileNotFoundError: Se o modelo não existir.
            RuntimeError: Se falhar ao criar a sessão.
        """
        model_path = Path(model_path)
        path_key = str(model_path.resolve())

        # Retornar sessão em cache se já carregada
        if path_key in self._sessions:
            logger.debug(
                f"Modelo já carregado (cache): {model_path.name}",
                source="RUNTIME",
            )
            return self._sessions[path_key]

        if not model_path.exists():
            raise FileNotFoundError(f"Modelo não encontrado: {model_path}")

        try:
            import onnxruntime as ort

            session_options = ort.SessionOptions()
            session_options.graph_optimization_level = (
                ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            )

            session = ort.InferenceSession(
                str(model_path),
                sess_options=session_options,
                providers=[self._provider],
            )

            self._sessions[path_key] = session

            logger.info(
                f"Modelo carregado: {model_path.name} "
                f"[{self._provider}]",
                source="RUNTIME",
            )

            return session

        except Exception as e:
            logger.error(
                f"Falha ao carregar modelo {model_path.name}: {e}",
                source="RUNTIME",
            )
            raise RuntimeError(f"Falha ao carregar modelo: {e}") from e

    def run_inference(
        self, session: Any, input_data: np.ndarray
    ) -> np.ndarray:
        """
        Executa inferência em um modelo ONNX carregado.

        Args:
            session: Sessão ONNX (retornada por load_model).
            input_data: Dados de entrada como numpy array.

        Returns:
            Output do modelo como numpy array.
        """
        input_name = session.get_inputs()[0].name
        output_names = [o.name for o in session.get_outputs()]

        result = session.run(output_names, {input_name: input_data})

        return result[0]

    def get_device_info(self) -> dict[str, str]:
        """Retorna informações sobre o dispositivo e provider ativo."""
        return dict(self._device_info)

    def get_provider_display_name(self) -> str:
        """Retorna um nome legível do provider para exibição na UI."""
        names = {
            "CUDAExecutionProvider": "🟢 NVIDIA GPU (CUDA)",
            "DmlExecutionProvider": "🟢 GPU (DirectML)",
            "OpenVINOExecutionProvider": "🟡 CPU Otimizada (OpenVINO)",
            "CPUExecutionProvider": "⚪ CPU",
        }
        return names.get(self._provider, self._provider)

    def unload_all(self):
        """Descarrega todos os modelos da memória."""
        count = len(self._sessions)
        self._sessions.clear()
        logger.info(
            f"{count} modelo(s) descarregado(s) da memória",
            source="RUNTIME",
        )
