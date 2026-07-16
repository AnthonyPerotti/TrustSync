"""
TrustSync — Path Resolution Helper

Gerencia a resolução de caminhos para funcionamento 100% standalone.
Compatível com modo de desenvolvimento e modo congelado (PyInstaller/sys._MEIPASS).
"""

import os
import sys
from pathlib import Path


def get_base_path() -> Path:
    """
    Retorna o diretório base da aplicação.

    Em modo PyInstaller (_MEIPASS), retorna a raiz extraída/empacotada.
    Em modo desenvolvimento, retorna o diretório raiz do repositório TrustSync.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # Rodando como executável congelado via PyInstaller
        return Path(sys._MEIPASS)
    else:
        # Rodando via Python interativo/script (raiz do projeto é parent de 'src')
        return Path(__file__).resolve().parent.parent.parent


def get_bin_path(binary_name: str) -> Path:
    """
    Retorna o caminho absoluto para um binário na pasta src/bin ou bin/.

    Args:
        binary_name: Nome do binário (ex: 'exiftool.exe' ou 'exiftool')

    Returns:
        Caminho resolvido para o binário.
    """
    base = get_base_path()
    
    # Se congelado, o PyInstaller colocará em bin/ ou src/bin dependendo da spec.
    paths_to_try = [
        base / "src" / "bin" / binary_name,
        base / "bin" / binary_name,
        base / binary_name,
    ]

    for p in paths_to_try:
        if p.exists():
            return p

    return base / "src" / "bin" / binary_name


def get_model_path(model_name: str) -> Path:
    """
    Retorna o caminho absoluto para um modelo ONNX na pasta src/models ou models/.

    Args:
        model_name: Nome do arquivo (ex: 'wav2vec2_deepfake.onnx')

    Returns:
        Caminho resolvido para o modelo.
    """
    base = get_base_path()
    paths_to_try = [
        base / "src" / "models" / model_name,
        base / "models" / model_name,
    ]

    for p in paths_to_try:
        if p.exists():
            return p

    return base / "src" / "models" / model_name
