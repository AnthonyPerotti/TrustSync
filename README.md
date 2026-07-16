# TrustSync

**Perícia Forense de Mídia com Detecção de Manipulação por IA**

Aplicação desktop para análise forense de arquivos de mídia (áudio, vídeo e documentos), com detecção de manipulação por inteligência artificial. Processamento 100% local, sem envio de dados para a nuvem.

## Funcionalidades

- 🔍 **Análise de Áudio** — Detecção de deepfake de voz via Wav2Vec2
- 🎬 **Análise de Vídeo** — Detecção de manipulação visual via MobileNetV3
- 📄 **Análise de Documentos** — Verificação de integridade de metadados
- 🚦 **Semáforo Visual** — Indicador Verde/Amarelo/Vermelho de confiança
- 📋 **Log de Auditoria** — Registro detalhado de cada análise
- ⚡ **GPU Acelerada** — ONNX Runtime com CUDA/DirectML, fallback OpenVINO

## Instalação

```bash
# Criar ambiente virtual
python -m venv venv
venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt
```

## Uso

```bash
python main.py
```

## Estrutura

```
src/
├── ui/          # Interface PySide6 (View)
├── controller/  # Lógica de controle (Controller)
├── engine/      # Inferência e processamento (Model)
├── models/      # Arquivos .onnx (Modelos de IA)
├── bin/         # Binários externos standalone (ex: exiftool.exe)
└── utils/       # Utilitários (paths, metadados, hash, log)
```

## Empacotamento Standalone (.exe via PyInstaller)

O TrustSync foi projetado para ser 100% autônomo (portátil). Para gerar o executável sem dependências externas no PC do utilizador final:

1. Certifique-se de que o **ExifTool** foi colocado em `src/bin/exiftool.exe` (veja [src/bin/README.md](file:///c:/Users/spisp/OneDrive/Documentos/deepshield/TrustSync/src/bin/README.md)).
2. Certifique-se de que os modelos `.onnx` estão em `src/models/`.
3. Execute o comando do PyInstaller com a especificação pré-configurada em modo `one-folder`:

```bash
pyinstaller build_app.spec --clean
```

O executável portátil final será gerado na pasta `dist/TrustSync/TrustSync.exe`. Todo o programa e suas dependências (modelos, binários e bibliotecas) estarão contidos nessa pasta.

## Requisitos de Sistema (Modo Desenvolvimento)

- Python 3.10+
- GPU NVIDIA com CUDA (opcional, para aceleração via ONNX Runtime / DirectML)
