"""
TrustSync — Extrator de Metadados Híbrido (ExifTool + Pillow + C2PA/Signatures)

Extrai e analisa metadados de arquivos de mídia, identificando campos suspeitos
que indicam manipulação ou geração por IA (ChatGPT, DALL-E, Midjourney, etc.).
Funciona de forma 100% autônoma via Python/Pillow mesmo se o ExifTool externo
não estiver presente no sistema.
"""

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Optional

from PIL import Image, ExifTags

from src.utils.logger import ForensicLogger
from src.utils.paths import get_bin_path

logger = ForensicLogger()

# Tags que indicam possível manipulação ou geração por IA em metadados de texto
SUSPICIOUS_SOFTWARE_TAGS = [
    "stable diffusion", "midjourney", "dall-e", "dalle", "chatgpt", "openai",
    "deepfake", "faceswap", "faceapp", "reface",
    "synthesia", "d-id", "heygen", "elevenlabs",
    "tortoise", "bark", "coqui", "rvc", "so-vits",
    "adobe firefly", "generative fill", "content-aware",
    "runway", "pika", "sora", "kling", "c2pa", "jumbf", "ai generated",
]

# Assinaturas binárias robustas e inequívocas para scan no fluxo de bytes bruto (evita falsos positivos como 'rvc')
BINARY_SIGNATURES = [
    "c2pa", "jumbf", "dall-e", "dalle", "chatgpt", "openai", "midjourney",
    "stable diffusion", "adobe firefly", "generative fill", "synthesia",
    "elevenlabs", "heygen", "runway", "ai generated",
]

# Tags de metadados que ferramentas de IA costumam alterar ou criar
AI_METADATA_FIELDS = [
    "Software", "Creator", "Producer", "CreatorTool",
    "HistorySoftwareAgent", "XMP:CreatorTool",
    "PNG:Software", "EXIF:Software",
    "Description", "Comment", "UserComment", "parameters", "prompt",
    "EmbeddedSignature", "tEXt", "iTXt", "zTXt", "XML:com.adobe.xmp",
]


class MetadataExtractor:
    """
    Extrai metadados de arquivos usando motor nativo (Pillow + Scan de Assinaturas)
    e ExifTool (se disponível), analisando indicadores de IA com máxima precisão.
    """

    def __init__(self, exiftool_path: Optional[str] = None):
        if exiftool_path:
            self._exiftool_path = str(exiftool_path)
        else:
            self._exiftool_path = str(get_bin_path("exiftool.exe"))
        self._available: Optional[bool] = None

    def is_available(self) -> bool:
        """Verifica se o ExifTool externo está disponível no sistema."""
        if self._available is not None:
            return self._available

        try:
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            result = subprocess.run(
                [self._exiftool_path, "-ver"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=creation_flags,
            )
            self._available = result.returncode == 0
            if self._available:
                version = result.stdout.strip()
                logger.info(f"ExifTool v{version} detectado em {self._exiftool_path}", source="METADATA")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self._available = False
            logger.info("ExifTool externo não encontrado — usando motor nativo Python (Pillow + C2PA scanner)", source="METADATA")

        return self._available

    def _extract_native(self, file_path: Path) -> dict[str, Any]:
        """
        Extrai metadados nativamente com Pillow e busca por assinaturas de IA/C2PA no fluxo do arquivo.
        Garantia de que PNGs do ChatGPT / DALL-E sejam detectados mesmo sem ExifTool.
        """
        native_meta: dict[str, Any] = {}

        # 1. Tentar ler metadados com Pillow para imagens
        ext = file_path.suffix.lower()
        if ext in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif", ".gif", ".heic"}:
            try:
                with Image.open(file_path) as img:
                    # Copiar todo img.info (contém parâmetros de IA, tEXt de PNGs, comentários)
                    for k, v in img.info.items():
                        if isinstance(v, (str, bytes, int, float)):
                            native_meta[f"PNG:{k}" if ext == ".png" else str(k)] = str(v)

                    # Extrair EXIF estruturado
                    exif_data = img.getexif()
                    if exif_data:
                        for tag_id, val in exif_data.items():
                            tag_name = ExifTags.TAGS.get(tag_id, f"Tag_{tag_id}")
                            if isinstance(val, (str, bytes, int, float)):
                                native_meta[f"EXIF:{tag_name}"] = str(val)
            except Exception as e:
                logger.debug(f"Pillow leitura nativa falhou ou incompleta para {file_path.name}: {e}", source="METADATA")

        # 2. Escaneamento rápido de assinaturas no binário (C2PA, JUMBF, DALL-E, ChatGPT)
        try:
            with open(file_path, "rb") as f:
                # Ler até os primeiros 128 KB para inspecionar cabeçalhos e blocos de metadados
                header_bytes = f.read(131072)
                # Também ler os últimos 64 KB onde blocos EXIF/IEND/C2PA costumam ficar anexados
                try:
                    f.seek(-65536, 2)
                    tail_bytes = f.read()
                except Exception:
                    tail_bytes = b""
                
                content_sample = header_bytes + b" " + tail_bytes
                content_lower = content_sample.lower()

                for tag in BINARY_SIGNATURES:
                    tag_bytes = tag.encode("utf-8")
                    if tag_bytes in content_lower:
                        native_meta["EmbeddedSignature"] = f"Assinatura/Referência gerada por IA detectada no arquivo: '{tag}'"
                        break
        except Exception as e:
            logger.debug(f"Erro no scan de assinaturas em {file_path.name}: {e}", source="METADATA")

        return native_meta

    def extract(self, file_path: str | Path) -> dict[str, Any]:
        """
        Extrai todos os metadados de um arquivo combinando o motor nativo e o ExifTool.
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        # Começar com metadados nativos (sempre funciona 100%)
        metadata = self._extract_native(file_path)

        # Enriquecer com ExifTool caso disponível
        if self.is_available():
            try:
                creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                result = subprocess.run(
                    [self._exiftool_path, "-j", "-G", "-n", str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    creationflags=creation_flags,
                )
                if result.returncode == 0:
                    metadata_list = json.loads(result.stdout)
                    if metadata_list and isinstance(metadata_list[0], dict):
                        for k, v in metadata_list[0].items():
                            metadata[k] = v
            except Exception as e:
                logger.debug(f"ExifTool extração falhou, mantendo dados nativos: {e}", source="METADATA")

        logger.info(
            f"Extraídos {len(metadata)} campos de metadados de '{file_path.name}'",
            source="METADATA",
        )

        return metadata

    def analyze_suspicion(
        self, metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Analisa metadados em busca de indicadores precisos de manipulação ou geração por IA.
        """
        findings: list[str] = []
        checked_fields = 0

        # 1. Verificar campos e valores em todo o dicionário de metadados
        for key, value in metadata.items():
            if not isinstance(value, str):
                continue
            
            checked_fields += 1
            value_lower = value.lower()

            for suspicious_tag in SUSPICIOUS_SOFTWARE_TAGS:
                # Evitar falsos positivos se a própria palavra for o nome do arquivo sendo inspecionado
                if "filename" in key.lower() or "directory" in key.lower():
                    continue

                # Se a tag for curta (ex: 'rvc', 'bark', 'pika'), exigir que seja palavra completa delimitada
                if len(suspicious_tag) <= 4:
                    if not re.search(rf'\b{re.escape(suspicious_tag)}\b', value_lower):
                        continue
                elif suspicious_tag not in value_lower:
                    continue

                findings.append(
                    f"Metadado '{key}' indica geração por IA ou edição sintética: '{value[:120]}'"
                )
                break

        # 2. Verificar inconsistências de data (apenas quando existirem múltiplas datas EXIF genuínas)
        dates = {}
        for key, value in metadata.items():
            if "date" in key.lower() and isinstance(value, str) and "filename" not in key.lower():
                dates[key] = value

        if len(set(dates.values())) > 2 and len(dates) >= 3:
            findings.append(
                f"Inconsistência de datas detectada: {len(set(dates.values()))} datas diferentes no mesmo arquivo"
            )

        # 3. Verificar se metadados de câmera foram removidos em fotos JPEG (não punir PNG de screenshots!)
        file_type = str(metadata.get("File:FileTypeExtension", "")).lower()
        if file_type in {"jpg", "jpeg"}:
            essential_fields = ["EXIF:Make", "EXIF:Model", "EXIF:DateTimeOriginal"]
            missing_essential = [
                f for f in essential_fields
                if not any(f.lower() in k.lower() for k in metadata.keys())
            ]
            if missing_essential and len(metadata) > 10:
                findings.append(
                    f"Foto JPEG com stripping de metadados originais de câmera ({', '.join(missing_essential)})"
                )

        # Calcular score de suspeitabilidade (se houver assinatura explícita de IA como ChatGPT/DALL-E, score é máximo)
        if any("geração por ia" in f.lower() or "c2pa" in f.lower() or "dall-e" in f.lower() or "chatgpt" in f.lower() for f in findings):
            suspicion_score = 0.95
        else:
            suspicion_score = min(1.0, len(findings) * 0.35)

        for finding in findings:
            logger.warning(finding, source="METADATA")

        return {
            "suspicious": len(findings) > 0,
            "score": suspicion_score,
            "findings": findings,
            "checked_fields": checked_fields,
        }
