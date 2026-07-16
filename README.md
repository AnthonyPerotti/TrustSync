# TrustSync

**Media Forensic Analysis with AI Manipulation Detection**

A desktop application for forensic analysis of media files (audio, video, and documents), featuring artificial intelligence manipulation detection. 100% local processing, with no data sent to the cloud.

## Features

- **Audio Analysis** — Voice deepfake detection via Wav2Vec2
- **Video Analysis** — Visual manipulation detection via MobileNetV3
- **Document Analysis** — Metadata integrity verification
- **Visual Traffic Light** — Green/Yellow/Red trust indicator
- **Audit Log** — Detailed record of each analysis
- **GPU Accelerated** — ONNX Runtime with CUDA/DirectML, OpenVINO fallback

## Installation

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

## Project Structure

```
src/
├── ui/          # PySide6 Interface (View)
├── controller/  # Control Logic (Controller)
├── engine/      # Inference and Processing (Model)
├── models/      # .onnx files (AI Models)
├── bin/         # External standalone binaries (e.g., exiftool.exe)
└── utils/       # Utilities (paths, metadata, hashes, logging)
```

## Standalone Packaging (.exe via PyInstaller)

TrustSync is designed to be 100% standalone (portable). To generate the executable without external dependencies on the end user's PC:

1. Ensure **ExifTool** has been placed in `src/bin/exiftool.exe` (see [src/bin/README.md](file:///c:/Users/spisp/OneDrive/Documentos/deepshield/TrustSync/src/bin/README.md)).
2. Ensure the `.onnx` models are placed in `src/models/`.
3. Run the PyInstaller command using the pre-configured spec in `one-folder` mode:

```bash
pyinstaller build_app.spec --clean
```

The final portable executable will be generated in the `dist/TrustSync/TrustSync.exe` folder. The entire program and its dependencies (models, binaries, and libraries) will be contained within that directory.

## System Requirements (Development Mode)

- Python 3.10+
- NVIDIA GPU with CUDA (optional, for acceleration via ONNX Runtime / DirectML)
