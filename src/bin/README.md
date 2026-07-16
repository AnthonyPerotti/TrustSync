# Binários Externos (TrustSync Standalone)

Para que o **TrustSync** funcione de maneira 100% portátil e seja empacotado corretamente pelo PyInstaller sem requerer nenhuma instalação prévia no PC do usuário, você deve colocar o executável do ExifTool dentro desta pasta (`src/bin/`).

## Instruções para o ExifTool no Windows

1. Baixe o executável autônomo do ExifTool do site oficial ([exiftool.org](https://exiftool.org/)).
2. Descompacte o arquivo zip baixado.
3. Você encontrará o arquivo `exiftool(-k).exe`.
4. Renomeie o arquivo de `exiftool(-k).exe` para **`exiftool.exe`**.
5. Copie `exiftool.exe` para **esta pasta (`src/bin/`)**.

A estrutura correta ficará assim:
```
TrustSync/
└── src/
    └── bin/
        ├── exiftool.exe    <--- COPIE AQUI
        ├── __init__.py
        └── README.md
```

Durante o build via PyInstaller (`build_app.spec`), todo o conteúdo de `src/bin` será empacotado junto ao executável principal, garantindo portabilidade.
