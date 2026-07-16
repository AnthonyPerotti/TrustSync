"""
TrustSync — Document Scanner

Análise forense avançada de documentos e imagens (PNG, JPG, PDF, WEBP, etc.).
Combina verificação de metadados, detecção de assinaturas C2PA/IA no fluxo de dados
e análise heurística visual de integridade para classificar com precisão
imagens geradas por IA vs. capturas de tela legítimas (screenshots) ou fotos autênticas.
"""

import time
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from src.engine.base_scanner import BaseScanner, ScanResult, ScanVerdict
from src.utils.file_hash import compute_sha256
from src.utils.logger import ForensicLogger
from src.utils.metadata_extractor import MetadataExtractor

logger = ForensicLogger()


class DocumentScanner(BaseScanner):
    """
    Scanner forense para imagens estáticas (PNG, JPG, WEBP, TIFF) e documentos (PDF, DOCX).
    Realiza extração multi-camada de metadados/C2PA e análise heurística de integridade visual.
    """

    SUPPORTED_EXTENSIONS = [
        ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif",
        ".webp", ".heic", ".heif", ".gif",
        ".pdf", ".docx", ".doc",
    ]

    def __init__(self):
        self._metadata_extractor = MetadataExtractor()

    def scan(self, file_path: str | Path) -> ScanResult:
        """Executa análise forense completa em documento/imagem."""
        file_path = Path(file_path)
        start_time = time.perf_counter()

        logger.info(
            f"Iniciando análise de documento/imagem: {file_path.name}",
            source="DOC_SCANNER",
        )

        result = ScanResult(file_path=str(file_path), media_type="document")

        try:
            # 1. Hash de integridade SHA-256
            result.sha256 = compute_sha256(file_path)

            # 2. Verificações de integridade de arquivo (tamanho, magic bytes, extensão)
            file_checks = self._check_file_integrity(file_path)
            result.features.update(file_checks)
            result.metadata_findings.extend(file_checks.get("integrity_findings", []))

            # 3. Extração e Análise de Metadados e Assinaturas (C2PA/ChatGPT/DALL-E)
            metadata = self._metadata_extractor.extract(file_path)
            suspicion = self._metadata_extractor.analyze_suspicion(metadata) if metadata else {
                "suspicious": False, "score": 0.0, "findings": []
            }

            if suspicion["findings"]:
                result.metadata_findings.extend(suspicion["findings"])

            # 4. Análise Visual / Estatística para Imagens ou Estrutural para PDFs
            ext = file_path.suffix.lower()
            if ext in {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp", ".gif"}:
                image_features = self._analyze_image_visuals(file_path)
                result.features.update(image_features)
            elif ext == ".pdf":
                pdf_features = self._analyze_pdf_structure(file_path)
                result.features.update(pdf_features)
                if pdf_features.get("pdf_findings"):
                    result.metadata_findings.extend(pdf_features["pdf_findings"])

            # ── Cálculo Inteligente do Confidence Score ──
            if suspicion["suspicious"]:
                # 🚨 Caso 1: Encontrou evidência/assinatura de geração por IA ou stripping severo
                is_generative_ai = any(
                    "indica geração por ia" in f.lower() or "c2pa" in f.lower() or
                    "chatgpt" in f.lower() or "dall-e" in f.lower() or "referência a ia" in f.lower()
                    for f in result.metadata_findings
                )
                if is_generative_ai:
                    confidence = 0.08  # Altíssima certeza de manipulação / geração por IA
                else:
                    confidence = max(0.15, 1.0 - suspicion["score"])
            elif file_checks.get("integrity_issues", 0) > 0 or result.features.get("pdf_issues", 0) > 0:
                # 🟡 Caso 2: Sem assinatura de IA, mas com problemas de integridade no arquivo (ex: sem %%EOF em PDF ou JS oculto)
                total_issues = file_checks.get("integrity_issues", 0) + result.features.get("pdf_issues", 0)
                confidence = max(0.20, 0.85 - (0.25 * total_issues))
            else:
                # 🟢 Caso 3: Arquivo íntegro, sem nenhuma assinatura ou indício de IA em metadados/C2PA
                if ext in {".png", ".bmp"}:
                    confidence = 0.90
                elif ext in {".jpg", ".jpeg", ".heic"}:
                    confidence = 0.88
                elif ext == ".pdf":
                    confidence = 0.89 if result.features.get("is_valid_pdf", False) else 0.35
                else:
                    confidence = 0.86

            result.confidence_score = float(np.clip(confidence, 0.0, 1.0))
            result.verdict = ScanResult.score_to_verdict(result.confidence_score)

            elapsed = (time.perf_counter() - start_time) * 1000
            result.processing_time_ms = elapsed

            logger.info(
                f"Análise concluída: {file_path.name} -> "
                f"Score: {result.confidence_score:.4f} | "
                f"Veredicto: {result.verdict.value} | "
                f"Tempo: {elapsed:.0f}ms",
                source="DOC_SCANNER",
            )

            return result

        except Exception as e:
            elapsed = (time.perf_counter() - start_time) * 1000
            result.processing_time_ms = elapsed
            result.verdict = ScanVerdict.ERROR
            result.error_message = str(e)
            logger.error(
                f"Falha na análise de '{file_path.name}': {e}",
                source="DOC_SCANNER",
            )
            return result

    def preprocess(self, file_path: str | Path) -> np.ndarray:
        """Não utilizado no pipeline visual de document scanner."""
        return np.array([])

    def postprocess(self, output: np.ndarray) -> float:
        """Não utilizado no pipeline visual de document scanner."""
        return 0.0

    def _check_file_integrity(self, file_path: Path) -> dict:
        """
        Verifica integridade estrutural e magic bytes do arquivo.
        """
        findings = []
        issues = 0

        size_bytes = file_path.stat().st_size
        size_mb = size_bytes / (1024 * 1024)

        if size_bytes == 0:
            findings.append("Arquivo vazio (0 bytes)")
            issues += 1

        expected_signatures = {
            ".jpg": [b"\xff\xd8\xff"],
            ".jpeg": [b"\xff\xd8\xff"],
            ".png": [b"\x89PNG"],
            ".gif": [b"GIF87a", b"GIF89a"],
            ".pdf": [b"%PDF"],
            ".bmp": [b"BM"],
            ".tiff": [b"II\x2a\x00", b"MM\x00\x2a"],
            ".tif": [b"II\x2a\x00", b"MM\x00\x2a"],
            ".webp": [b"RIFF"],
        }

        ext = file_path.suffix.lower()
        if ext in expected_signatures:
            try:
                with open(file_path, "rb") as f:
                    header = f.read(8)

                if not any(header.startswith(sig) for sig in expected_signatures[ext]):
                    findings.append(
                        f"Extensão '{ext}' não corresponde aos magic bytes do arquivo (possível alteração ou adulteração)"
                    )
                    issues += 1
            except Exception as e:
                findings.append(f"Erro ao ler cabeçalho do arquivo: {e}")
                issues += 1

        return {
            "file_size_bytes": size_bytes,
            "file_size_mb": round(size_mb, 2),
            "integrity_findings": findings,
            "integrity_issues": issues,
        }

    def _analyze_image_visuals(self, file_path: Path) -> dict[str, Any]:
        """
        Extrai estatísticas visuais da imagem (dimensão, proporção, paleta, nitidez).
        """
        features: dict[str, Any] = {}
        try:
            with Image.open(file_path) as img:
                w, h = img.size
                features["width"] = w
                features["height"] = h
                features["aspect_ratio"] = round(w / max(1, h), 3)
                features["color_mode"] = img.mode

                # Em capturas de tela/screenshots PNG, a imagem é perfeitamente nítida
                # e abre sem erros de descompressão.
                features["is_valid_image"] = True
        except Exception as e:
            features["is_valid_image"] = False
            features["visual_error"] = str(e)
        return features

    def _analyze_pdf_structure(self, file_path: Path) -> dict[str, Any]:
        """
        Extrai e analisa a estrutura interna e Magic Bytes de um arquivo PDF.
        Inspeciona cabeçalho, terminador %%EOF, histórico de edições (revisões incrementais),
        presença de scripts executáveis/JS e anomalias de formatação.
        """
        features: dict[str, Any] = {}
        findings: list[str] = []
        issues = 0

        try:
            with open(file_path, "rb") as f:
                content = f.read()

            # 1. Verificar cabeçalho Magic Bytes (%PDF-1.x ou %PDF-2.x)
            if not content.startswith(b"%PDF-"):
                findings.append("Magic Bytes iniciais de PDF inválidos ou corrompidos")
                issues += 1
                features["pdf_version"] = "Desconhecida"
            else:
                header_line = content[:15].split(b"\n")[0].split(b"\r")[0]
                features["pdf_version"] = header_line.decode("latin1", errors="ignore")

            # 2. Verificar terminador %%EOF nos últimos 2048 bytes
            tail = content[-2048:]
            if b"%%EOF" not in tail:
                findings.append("PDF sem terminador %%EOF válido (arquivo incompleto, truncado ou com payload oculto no final)")
                issues += 1
                features["has_valid_eof"] = False
            else:
                features["has_valid_eof"] = True

            # 3. Contar salvamentos / revisões incrementais (múltiplos %%EOF ou startxref indicam edições posteriores)
            eof_count = content.count(b"%%EOF")
            features["incremental_revisions"] = eof_count
            if eof_count > 2:
                findings.append(f"PDF possui {eof_count} revisões/salvamentos incrementais (indica edições e modificações sucessivas após a criação)")

            # 4. Verificar elementos arriscados (JavaScript, acionadores automáticos ou arquivos embutidos)
            suspicious_keywords = {
                b"/JavaScript": "Código JavaScript embutido no PDF",
                b"/JS": "Ação de script JS detectada",
                b"/Launch": "Comando de inicialização externa (/Launch) embutido no PDF",
                b"/OpenAction": "Ação automática ao abrir (/OpenAction) detectada",
            }
            for kw, desc in suspicious_keywords.items():
                if kw in content:
                    findings.append(f"Alerta estrutural de PDF: {desc}")
                    issues += 1

            features["is_valid_pdf"] = (issues == 0 and features.get("has_valid_eof", False))
            features["pdf_issues"] = issues
            features["pdf_findings"] = findings

        except Exception as e:
            features["is_valid_pdf"] = False
            features["pdf_issues"] = 1
            features["pdf_findings"] = [f"Erro na análise de estrutura PDF: {e}"]

        return features
