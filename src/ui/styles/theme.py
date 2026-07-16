"""
TrustSync — Dark Forensic Theme

Tema escuro profissional para a interface forense.
Paleta baseada em tons escuros com acentos ciano para
dar um visual técnico/forense premium.
"""

# ─── Paleta de Cores ──────────────────────────────────────────

COLORS = {
    # Backgrounds
    "bg_primary": "#0a0e17",      # Fundo principal (quase preto azulado)
    "bg_secondary": "#111827",     # Painéis e cards
    "bg_tertiary": "#1e293b",      # Inputs e áreas de drop
    "bg_hover": "#283548",         # Hover em elementos interativos
    "bg_surface": "#0f172a",       # Superfícies elevadas

    # Texto
    "text_primary": "#e2e8f0",     # Texto principal
    "text_secondary": "#94a3b8",   # Texto secundário
    "text_muted": "#64748b",       # Texto desabilitado

    # Accent — Ciano Forense
    "accent": "#06b6d4",           # Ciano principal
    "accent_hover": "#22d3ee",     # Ciano hover
    "accent_dim": "#0e7490",       # Ciano escuro

    # Semáforo
    "green": "#22c55e",            # Autêntico
    "green_glow": "#16a34a",
    "yellow": "#eab308",           # Inconclusivo
    "yellow_glow": "#ca8a04",
    "red": "#ef4444",              # Manipulado
    "red_glow": "#dc2626",

    # Status
    "info": "#38bdf8",
    "warning": "#f59e0b",
    "error": "#ef4444",
    "success": "#22c55e",

    # Bordas
    "border": "#1e293b",
    "border_focus": "#06b6d4",
}


def get_stylesheet() -> str:
    """Retorna o QSS stylesheet completo do tema escuro forense."""
    c = COLORS
    return f"""
    /* ═══════════════════════════════════════════════════════════
       TrustSync — Dark Forensic Theme
       ═══════════════════════════════════════════════════════════ */

    /* ── Global ─────────────────────────────────────────────── */
    QWidget {{
        background-color: {c["bg_primary"]};
        color: {c["text_primary"]};
        font-family: "Segoe UI", "Inter", "Roboto", sans-serif;
        font-size: 13px;
    }}

    /* ── Main Window ────────────────────────────────────────── */
    QMainWindow {{
        background-color: {c["bg_primary"]};
    }}

    QMainWindow::separator {{
        background-color: {c["border"]};
        width: 1px;
        height: 1px;
    }}

    /* ── Menu Bar ───────────────────────────────────────────── */
    QMenuBar {{
        background-color: {c["bg_surface"]};
        color: {c["text_primary"]};
        border-bottom: 1px solid {c["border"]};
        padding: 4px 8px;
    }}

    QMenuBar::item {{
        padding: 6px 12px;
        border-radius: 4px;
    }}

    QMenuBar::item:selected {{
        background-color: {c["bg_hover"]};
    }}

    QMenu {{
        background-color: {c["bg_secondary"]};
        border: 1px solid {c["border"]};
        border-radius: 8px;
        padding: 4px;
    }}

    QMenu::item {{
        padding: 8px 24px;
        border-radius: 4px;
    }}

    QMenu::item:selected {{
        background-color: {c["accent_dim"]};
        color: white;
    }}

    /* ── Status Bar ─────────────────────────────────────────── */
    QStatusBar {{
        background-color: {c["bg_surface"]};
        color: {c["text_secondary"]};
        border-top: 1px solid {c["border"]};
        padding: 4px 12px;
        font-size: 12px;
    }}

    /* ── Labels ─────────────────────────────────────────────── */
    QLabel {{
        color: {c["text_primary"]};
        background: transparent;
    }}

    QLabel#title {{
        font-size: 18px;
        font-weight: bold;
        color: {c["accent"]};
    }}

    QLabel#subtitle {{
        font-size: 12px;
        color: {c["text_secondary"]};
    }}

    /* ── Buttons ────────────────────────────────────────────── */
    QPushButton {{
        background-color: {c["accent_dim"]};
        color: white;
        border: 1px solid {c["accent"]};
        border-radius: 6px;
        padding: 8px 20px;
        font-weight: 600;
        font-size: 13px;
    }}

    QPushButton:hover {{
        background-color: {c["accent"]};
        border-color: {c["accent_hover"]};
    }}

    QPushButton:pressed {{
        background-color: {c["accent_dim"]};
    }}

    QPushButton:disabled {{
        background-color: {c["bg_tertiary"]};
        color: {c["text_muted"]};
        border-color: {c["border"]};
    }}

    QPushButton#cancelButton {{
        background-color: transparent;
        border-color: {c["red"]};
        color: {c["red"]};
    }}

    QPushButton#cancelButton:hover {{
        background-color: {c["red"]};
        color: white;
    }}

    /* ── Text Edit / Log Panel ──────────────────────────────── */
    QTextEdit {{
        background-color: {c["bg_surface"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 8px;
        padding: 12px;
        font-family: "Cascadia Code", "Consolas", "Fira Code", monospace;
        font-size: 12px;
        selection-background-color: {c["accent_dim"]};
    }}

    /* ── Progress Bar ───────────────────────────────────────── */
    QProgressBar {{
        background-color: {c["bg_tertiary"]};
        border: 1px solid {c["border"]};
        border-radius: 6px;
        height: 8px;
        text-align: center;
        font-size: 11px;
        color: {c["text_secondary"]};
    }}

    QProgressBar::chunk {{
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 {c["accent_dim"]},
            stop:1 {c["accent"]}
        );
        border-radius: 5px;
    }}

    /* ── Scroll Bars ────────────────────────────────────────── */
    QScrollBar:vertical {{
        background-color: {c["bg_primary"]};
        width: 10px;
        margin: 0px;
        border-radius: 5px;
    }}

    QScrollBar::handle:vertical {{
        background-color: {c["bg_hover"]};
        min-height: 30px;
        border-radius: 5px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {c["accent_dim"]};
    }}

    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background-color: {c["bg_primary"]};
        height: 10px;
        border-radius: 5px;
    }}

    QScrollBar::handle:horizontal {{
        background-color: {c["bg_hover"]};
        min-width: 30px;
        border-radius: 5px;
    }}

    /* ── Frames / Group Boxes ───────────────────────────────── */
    QFrame#panel {{
        background-color: {c["bg_secondary"]};
        border: 1px solid {c["border"]};
        border-radius: 12px;
    }}

    QGroupBox {{
        background-color: {c["bg_secondary"]};
        border: 1px solid {c["border"]};
        border-radius: 10px;
        margin-top: 16px;
        padding-top: 20px;
        font-weight: bold;
        color: {c["text_secondary"]};
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 8px;
        color: {c["accent"]};
    }}

    /* ── Tooltips ────────────────────────────────────────────── */
    QToolTip {{
        background-color: {c["bg_secondary"]};
        color: {c["text_primary"]};
        border: 1px solid {c["accent_dim"]};
        border-radius: 4px;
        padding: 6px 10px;
        font-size: 12px;
    }}

    /* ── File Dialog ─────────────────────────────────────────── */
    QFileDialog {{
        background-color: {c["bg_primary"]};
    }}
    """
