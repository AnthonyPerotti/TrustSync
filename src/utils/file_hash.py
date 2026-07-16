"""
TrustSync — Verificação de Integridade via Hash

Calcula SHA-256 em chunks para suporte a arquivos grandes,
permitindo verificação de integridade forense.
"""

import hashlib
from pathlib import Path

from src.utils.logger import ForensicLogger

# Tamanho do chunk: 8KB para balancear velocidade e uso de memória
CHUNK_SIZE = 8192

logger = ForensicLogger()


def compute_sha256(file_path: str | Path, chunk_size: int = CHUNK_SIZE) -> str:
    """
    Calcula o hash SHA-256 de um arquivo.

    Processa o arquivo em chunks para suportar arquivos grandes
    sem carregar tudo na memória.

    Args:
        file_path: Caminho para o arquivo.
        chunk_size: Tamanho do chunk em bytes (default: 8KB).

    Returns:
        Hash SHA-256 em hexadecimal (lowercase).

    Raises:
        FileNotFoundError: Se o arquivo não existir.
        PermissionError: Se não houver permissão de leitura.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

    if not file_path.is_file():
        raise ValueError(f"O caminho não é um arquivo: {file_path}")

    sha256 = hashlib.sha256()

    logger.debug(f"Calculando SHA-256 de: {file_path.name}", source="HASH")

    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            sha256.update(chunk)

    digest = sha256.hexdigest()
    logger.info(
        f"SHA-256 [{file_path.name}]: {digest[:16]}...{digest[-8:]}",
        source="HASH",
    )

    return digest


def verify_integrity(file_path: str | Path, expected_hash: str) -> bool:
    """
    Verifica se o hash de um arquivo corresponde ao esperado.

    Args:
        file_path: Caminho para o arquivo.
        expected_hash: Hash SHA-256 esperado.

    Returns:
        True se o hash corresponder, False caso contrário.
    """
    actual_hash = compute_sha256(file_path)
    match = actual_hash.lower() == expected_hash.lower()

    if match:
        logger.info(
            f"Integridade verificada: {Path(file_path).name}", source="HASH"
        )
    else:
        logger.warning(
            f"FALHA de integridade: {Path(file_path).name} "
            f"(esperado: {expected_hash[:16]}..., obtido: {actual_hash[:16]}...)",
            source="HASH",
        )

    return match
