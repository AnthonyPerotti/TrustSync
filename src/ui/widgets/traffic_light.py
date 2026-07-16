"""
TrustSync — Traffic Light Widget (Semáforo)

Widget customizado que desenha um semáforo forense com 3 indicadores
(Verde/Amarelo/Vermelho) e animação de transição suave.
Exibe o confidence score numérico abaixo.
"""

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QSize,
    Qt,
    Property,
)
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from src.ui.styles.theme import COLORS


class TrafficLightWidget(QWidget):
    """
    Widget de semáforo forense com animação de glow.

    Estados:
        - IDLE: Todos os indicadores apagados (aguardando)
        - GREEN: Autêntico (score ≥ 0.7)
        - YELLOW: Inconclusivo (0.4 ≤ score < 0.7)
        - RED: Manipulado (score < 0.4)
        - SCANNING: Animação pulsante durante análise
    """

    STATE_IDLE = "idle"
    STATE_GREEN = "green"
    STATE_YELLOW = "yellow"
    STATE_RED = "red"
    STATE_SCANNING = "scanning"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = self.STATE_IDLE
        self._score: float = 0.0
        self._glow_intensity: float = 0.0

        # Layout
        self._layout = QVBoxLayout(self)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.setContentsMargins(20, 20, 20, 20)

        # Score label
        self._score_label = QLabel("—")
        self._score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._score_label.setStyleSheet(
            f"font-size: 32px; font-weight: bold; "
            f"color: {COLORS['text_primary']}; background: transparent;"
        )

        # Verdict label
        self._verdict_label = QLabel("Aguardando arquivo...")
        self._verdict_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._verdict_label.setStyleSheet(
            f"font-size: 14px; color: {COLORS['text_secondary']}; "
            f"background: transparent;"
        )

        self._layout.addStretch()
        self._layout.addWidget(self._score_label)
        self._layout.addWidget(self._verdict_label)
        self._layout.addStretch()

        # Animação de glow
        self._glow_animation = QPropertyAnimation(self, b"glow_intensity")
        self._glow_animation.setDuration(800)
        self._glow_animation.setEasingCurve(QEasingCurve.Type.InOutSine)

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.setMinimumSize(200, 350)

    # ── Qt Property para animação ──

    def _get_glow_intensity(self) -> float:
        return self._glow_intensity

    def _set_glow_intensity(self, value: float):
        self._glow_intensity = value
        self.update()

    glow_intensity = Property(
        float, _get_glow_intensity, _set_glow_intensity
    )

    # ── API Pública ──

    def set_score(self, score: float):
        """
        Define o confidence score e atualiza o semáforo.

        Args:
            score: Valor entre 0.0 e 1.0.
        """
        self._score = max(0.0, min(1.0, score))

        if score >= 0.7:
            self._set_state(self.STATE_GREEN)
            verdict = "AUTÊNTICO"
            color = COLORS["green"]
        elif score >= 0.4:
            self._set_state(self.STATE_YELLOW)
            verdict = "INCONCLUSIVO"
            color = COLORS["yellow"]
        else:
            self._set_state(self.STATE_RED)
            verdict = "MANIPULADO"
            color = COLORS["red"]

        self._score_label.setText(f"{score:.1%}")
        self._score_label.setStyleSheet(
            f"font-size: 32px; font-weight: bold; "
            f"color: {color}; background: transparent;"
        )
        self._verdict_label.setText(verdict)
        self._verdict_label.setStyleSheet(
            f"font-size: 14px; font-weight: 600; "
            f"color: {color}; background: transparent;"
        )

    def set_scanning(self):
        """Ativa estado de scanning com animação pulsante."""
        self._set_state(self.STATE_SCANNING)
        self._score_label.setText("...")
        self._score_label.setStyleSheet(
            f"font-size: 32px; font-weight: bold; "
            f"color: {COLORS['accent']}; background: transparent;"
        )
        self._verdict_label.setText("Analisando...")
        self._verdict_label.setStyleSheet(
            f"font-size: 14px; color: {COLORS['accent']}; "
            f"background: transparent;"
        )

        # Animação pulsante
        self._glow_animation.setStartValue(0.2)
        self._glow_animation.setEndValue(1.0)
        self._glow_animation.setLoopCount(-1)  # Loop infinito
        self._glow_animation.start()

    def set_idle(self):
        """Volta ao estado idle (aguardando)."""
        self._set_state(self.STATE_IDLE)
        self._glow_animation.stop()
        self._glow_intensity = 0.0
        self._score = 0.0
        self._score_label.setText("—")
        self._score_label.setStyleSheet(
            f"font-size: 32px; font-weight: bold; "
            f"color: {COLORS['text_primary']}; background: transparent;"
        )
        self._verdict_label.setText("Aguardando arquivo...")
        self._verdict_label.setStyleSheet(
            f"font-size: 14px; color: {COLORS['text_secondary']}; "
            f"background: transparent;"
        )
        self.update()

    def set_error(self, message: str = "Erro na análise"):
        """Exibe estado de erro."""
        self._set_state(self.STATE_RED)
        self._glow_animation.stop()
        self._score_label.setText("✕")
        self._score_label.setStyleSheet(
            f"font-size: 32px; font-weight: bold; "
            f"color: {COLORS['red']}; background: transparent;"
        )
        self._verdict_label.setText(message)
        self._verdict_label.setStyleSheet(
            f"font-size: 14px; color: {COLORS['red']}; "
            f"background: transparent;"
        )

    def _set_state(self, state: str):
        """Define o estado interno e anima a transição."""
        if self._state == state:
            return

        self._state = state

        # Animar glow de transição (exceto scanning que tem loop próprio)
        if state != self.STATE_SCANNING:
            self._glow_animation.stop()
            self._glow_animation.setLoopCount(1)
            self._glow_animation.setStartValue(0.0)
            self._glow_animation.setEndValue(1.0)
            self._glow_animation.start()

    # ── Rendering ──

    def paintEvent(self, event):
        """Desenha os 3 indicadores do semáforo."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Dimensões do semáforo
        light_radius = min(w, h) // 8
        spacing = light_radius * 2.6
        center_x = w // 2
        start_y = h // 2 - spacing

        # Configurar cores por estado
        lights = [
            (self.STATE_RED, COLORS["red"], COLORS["red_glow"]),
            (self.STATE_YELLOW, COLORS["yellow"], COLORS["yellow_glow"]),
            (self.STATE_GREEN, COLORS["green"], COLORS["green_glow"]),
        ]

        # Fundo do semáforo (retângulo arredondado)
        bg_rect_x = center_x - light_radius - 20
        bg_rect_y = int(start_y - light_radius - 20)
        bg_rect_w = (light_radius + 20) * 2
        bg_rect_h = int(spacing * 2 + light_radius * 2 + 40)

        painter.setPen(QPen(QColor(COLORS["border"]), 2))
        painter.setBrush(QBrush(QColor(COLORS["bg_secondary"])))
        painter.drawRoundedRect(
            bg_rect_x, bg_rect_y, bg_rect_w, bg_rect_h, 20, 20
        )

        for i, (state, color_on, color_glow) in enumerate(lights):
            cy = int(start_y + i * spacing)
            is_active = self._state == state
            is_scanning = self._state == self.STATE_SCANNING

            if is_active:
                intensity = self._glow_intensity

                # Glow externo
                glow = QRadialGradient(center_x, cy, light_radius * 2)
                glow_color = QColor(color_glow)
                glow_color.setAlphaF(0.3 * intensity)
                glow.setColorAt(0.0, glow_color)
                glow_color_fade = QColor(color_glow)
                glow_color_fade.setAlphaF(0.0)
                glow.setColorAt(1.0, glow_color_fade)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(glow))
                painter.drawEllipse(
                    center_x - light_radius * 2,
                    cy - light_radius * 2,
                    light_radius * 4,
                    light_radius * 4,
                )

                # Círculo principal aceso
                gradient = QRadialGradient(
                    center_x - light_radius * 0.3,
                    cy - light_radius * 0.3,
                    light_radius,
                )
                bright = QColor(color_on)
                bright.setAlphaF(0.6 + 0.4 * intensity)
                gradient.setColorAt(0.0, bright.lighter(140))
                gradient.setColorAt(0.7, bright)
                gradient.setColorAt(1.0, QColor(color_glow))
                painter.setBrush(QBrush(gradient))

            elif is_scanning:
                # Todos pulsam sutilmente durante scanning
                dim = QColor(COLORS["accent_dim"])
                dim.setAlphaF(0.15 + 0.15 * self._glow_intensity)
                painter.setBrush(QBrush(dim))

            else:
                # Apagado
                dim = QColor(color_on)
                dim.setAlphaF(0.08)
                painter.setBrush(QBrush(dim))

            painter.setPen(
                QPen(QColor(COLORS["border"]), 1.5)
            )
            painter.drawEllipse(
                center_x - light_radius,
                cy - light_radius,
                light_radius * 2,
                light_radius * 2,
            )

        painter.end()

    def sizeHint(self) -> QSize:
        return QSize(220, 380)
