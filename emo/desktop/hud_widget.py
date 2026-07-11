"""Widgets HUD style MARK XLVIII — bulle holographique, métriques, thème."""
from __future__ import annotations

import math
import random
import re
import time

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QTextBrowser, QWidget

FONT_UI = "Segoe UI"
FONT_HUD = "Consolas"
_LEFT_W = 120
_RIGHT_W = 300


class C:
    BG_SOLID = "#010408"
    PANEL2 = "rgba(0, 18, 30, 0.18)"
    BORDER = "rgba(0, 180, 220, 0.14)"
    BORDER_B = "rgba(0, 220, 255, 0.45)"
    BORDER_A = "rgba(0, 140, 180, 0.22)"
    PRI = "#00d4e8"
    PRI_DIM = "rgba(0, 180, 210, 0.45)"
    PRI_GHO = "rgba(0, 60, 90, 0.12)"
    GOLD = "#b8a050"
    GOLD_DIM = "rgba(184, 160, 80, 0.35)"
    ACC = "#e8a060"
    ACC2 = "#e8d080"
    GREEN = "#40e8a8"
    MUTED_C = "#c06070"
    TEXT = "rgba(200, 235, 248, 0.90)"
    TEXT_DIM = "rgba(70, 130, 155, 0.65)"
    TEXT_MED = "rgba(130, 190, 215, 0.78)"
    BAR_BG = "rgba(0, 10, 20, 0.28)"


def qcol(h: str, a: int = 255) -> QColor:
    c = QColor(h)
    c.setAlpha(a)
    return c


def btn_style(fg: str = C.TEXT, bg: str = "transparent", hover: str | None = None, gold: bool = False) -> str:
    border = C.GOLD_DIM if gold else C.BORDER
    return (
        f"QPushButton {{ background: {bg}; color: {fg}; border: 1px solid {border};"
        f" border-radius: 4px; padding: 5px 10px; font-family: '{FONT_UI}'; font-size: 9pt; }}"
        f" QPushButton:hover {{ color: {hover or C.PRI}; border-color: {C.BORDER_B};"
        f" background: rgba(0,60,90,0.18); }}"
        f" QPushButton:pressed {{ background: rgba(0,100,140,0.28); }}"
    )




def app_stylesheet() -> str:
    return f"""
    QMainWindow, QWidget {{
        background: {C.BG_SOLID};
        color: {C.TEXT};
        font-family: '{FONT_UI}';
        font-size: 9pt;
    }}
    QLineEdit, QTextEdit {{
        background: rgba(0, 10, 20, 0.38);
        color: {C.TEXT};
        border: 1px solid {C.BORDER};
        border-radius: 4px;
        padding: 5px 8px;
    }}
    QLineEdit:focus, QTextEdit:focus {{ border-color: {C.BORDER_B}; }}
    QListWidget {{
        background: transparent;
        color: {C.TEXT};
        border: none;
    }}
    QScrollBar:vertical {{
        background: transparent; width: 6px; border-radius: 3px;
    }}
    QScrollBar::handle:vertical {{
        background: rgba(0, 180, 220, 0.35); border-radius: 3px; min-height: 24px;
    }}
    """


class MetricBar(QWidget):
    def __init__(self, label: str, color: str = C.PRI, parent=None):
        super().__init__(parent)
        self._label = label
        self._color = color
        self._value = 0.0
        self._text = "--"
        self.setFixedHeight(30)
        self.setMinimumWidth(80)

    def set_value(self, pct: float, text: str) -> None:
        self._value = max(0.0, min(100.0, pct))
        self._text = text
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.setBrush(QBrush(qcol(C.PANEL2, 120)))
        p.setPen(QPen(qcol(C.BORDER_A), 1))
        p.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), 4, 4)
        bar_h = 4
        bar_y, bar_w, bar_x = h - bar_h - 5, w - 12, 6
        fill_w = int(bar_w * self._value / 100)
        p.setBrush(QBrush(qcol(C.BAR_BG)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(QRectF(bar_x, bar_y, bar_w, bar_h))
        if self._value > 85:
            bar_col = qcol(C.MUTED_C)
        elif self._value > 65:
            bar_col = qcol(C.ACC)
        else:
            bar_col = qcol(self._color)
        if fill_w > 0:
            p.setBrush(QBrush(bar_col))
            p.drawRect(QRectF(bar_x, bar_y, fill_w, bar_h))
        p.setFont(QFont(FONT_HUD, 7, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.TEXT_DIM), 1))
        p.drawText(QRectF(8, 5, 50, 14), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._label)
        p.setFont(QFont(FONT_HUD, 9, QFont.Weight.Bold))
        p.setPen(QPen(bar_col if self._text != "--" else qcol(C.TEXT_DIM), 1))
        p.drawText(QRectF(0, 4, w - 6, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self._text)


class JournalWidget(QTextBrowser):
    _URL_RE = re.compile(r"(https?://[^\s<]+)")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setOpenExternalLinks(True)

    def append_line(self, text: str) -> None:
        tl = text.lower()
        if tl.startswith("vous:") or tl.startswith("you:"):
            color = C.TEXT
        elif tl.startswith("émo:") or tl.startswith("emo:"):
            color = C.PRI
        elif "erreur" in tl or "error" in tl:
            color = C.MUTED_C
        elif tl.startswith("sys:") or tl.startswith("["):
            color = C.ACC2
        else:
            color = C.TEXT_MED
        body = self._URL_RE.sub(
            r'<a href="\1" style="color:#7ec8ff">\1</a>',
            text.replace("&", "&amp;").replace("<", "&lt;"),
        )
        self.append(f'<span style="color:{color}">{body}</span>')


class HudCanvas(QWidget):
    """Bulle HUD centrale — anneaux, scanners, EMO, waveform (Mark XLVIII)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(300, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.muted = False
        self.speaking = False
        self.state = "LISTENING"
        self._tick = 0
        self._scale = 1.0
        self._tgt_scale = 1.0
        self._halo = 55.0
        self._tgt_halo = 55.0
        self._last_t = time.time()
        self._scan = 0.0
        self._scan2 = 180.0
        self._rings = [0.0, 120.0, 240.0]
        self._pulses: list[float] = [0.0, 50.0, 100.0]
        self._blink = True
        self._blink_tick = 0
        self._particles: list[list[float]] = []
        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self._tmr.start(16)

    def set_state(self, state: str) -> None:
        self.state = state
        self.speaking = state == "SPEAKING"
        self.muted = state == "MUTED"

    def _step(self) -> None:
        self._tick += 1
        now = time.time()
        if now - self._last_t > (0.12 if self.speaking else 0.5):
            if self.speaking:
                self._tgt_scale = random.uniform(1.06, 1.14)
                self._tgt_halo = random.uniform(145, 190)
            elif self.muted:
                self._tgt_scale = random.uniform(0.998, 1.002)
                self._tgt_halo = random.uniform(15, 28)
            else:
                self._tgt_scale = random.uniform(1.001, 1.008)
                self._tgt_halo = random.uniform(48, 68)
            self._last_t = now
        sp = 0.38 if self.speaking else 0.15
        self._scale += (self._tgt_scale - self._scale) * sp
        self._halo += (self._tgt_halo - self._halo) * sp
        speeds = [1.3, -0.9, 2.0] if self.speaking else [0.55, -0.35, 0.9]
        for i, spd in enumerate(speeds):
            self._rings[i] = (self._rings[i] + spd) % 360
        self._scan = (self._scan + (3.0 if self.speaking else 1.3)) % 360
        self._scan2 = (self._scan2 + (-2.0 if self.speaking else -0.75)) % 360
        fw = min(max(self.width(), 1), max(self.height(), 1))
        lim = fw * 0.74
        spd = 4.2 if self.speaking else 2.0
        self._pulses = [r + spd for r in self._pulses if r + spd < lim]
        if len(self._pulses) < 3 and random.random() < (0.07 if self.speaking else 0.025):
            self._pulses.append(0.0)
        if self.speaking and random.random() < 0.28:
            cx, cy = self.width() / 2, self.height() / 2
            ang = random.uniform(0, 2 * math.pi)
            r_s = fw * 0.28
            self._particles.append([
                cx + math.cos(ang) * r_s, cy + math.sin(ang) * r_s,
                math.cos(ang) * random.uniform(0.9, 2.4),
                math.sin(ang) * random.uniform(0.9, 2.4) - 0.4, 1.0,
            ])
        self._particles = [
            [p[0] + p[2], p[1] + p[3], p[2] * 0.97, p[3] * 0.97, p[4] - 0.028]
            for p in self._particles if p[4] > 0
        ]
        self._blink_tick += 1
        if self._blink_tick >= 38:
            self._blink = not self._blink
            self._blink_tick = 0
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), Qt.GlobalColor.transparent)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        fw = min(w, h)
        pri = C.MUTED_C if self.muted else C.PRI

        p.setPen(QPen(qcol(pri, 18), 1))
        for x in range(0, w, 56):
            for y in range(0, h, 56):
                p.drawPoint(x, y)

        r_face = fw * 0.31
        for i in range(12):
            r = r_face * (1.85 - i * 0.07)
            frc = 1.0 - i / 12
            a = max(0, min(255, int(self._halo * 0.07 * frc)))
            col = qcol(C.GOLD if i % 3 == 0 else pri, a)
            p.setPen(QPen(col, 1.2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        for pr in self._pulses:
            a = max(0, int(230 * (1.0 - pr / (fw * 0.74))))
            p.setPen(QPen(qcol(pri, a), 1.5))
            p.drawEllipse(QRectF(cx - pr, cy - pr, pr * 2, pr * 2))

        for idx, (r_frac, w_r, arc_l, gap) in enumerate(
            [(0.48, 3, 115, 78), (0.40, 2, 78, 55), (0.32, 1, 56, 40)]
        ):
            ring_r = fw * r_frac
            base = self._rings[idx]
            a_val = max(0, min(255, int(self._halo * (1.0 - idx * 0.18))))
            p.setPen(QPen(qcol(pri, a_val), w_r))
            rect = QRectF(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2)
            angle = base
            while angle < base + 360:
                p.drawArc(rect, int(angle * 16), int(arc_l * 16))
                angle += arc_l + gap

        sr = fw * 0.50
        sa = min(255, int(self._halo * 1.5))
        ex = 75 if self.speaking else 44
        srect = QRectF(cx - sr, cy - sr, sr * 2, sr * 2)
        p.setPen(QPen(qcol(pri, sa), 2.5))
        p.drawArc(srect, int(self._scan * 16), int(ex * 16))
        p.setPen(QPen(qcol(C.ACC, sa // 2), 1.5))
        p.drawArc(srect, int(self._scan2 * 16), int(ex * 16))

        t_out, t_in = fw * 0.497, fw * 0.474
        p.setPen(QPen(qcol(pri, 140), 1))
        for deg in range(0, 360, 10):
            rad = math.radians(deg)
            inn = t_in if deg % 30 == 0 else t_in + 6
            p.drawLine(
                QPointF(cx + t_out * math.cos(rad), cy - t_out * math.sin(rad)),
                QPointF(cx + inn * math.cos(rad), cy - inn * math.sin(rad)),
            )

        ch_r, gap_h = fw * 0.51, fw * 0.16
        p.setPen(QPen(qcol(pri, int(self._halo * 0.5)), 1))
        p.drawLine(QPointF(cx - ch_r, cy), QPointF(cx - gap_h, cy))
        p.drawLine(QPointF(cx + gap_h, cy), QPointF(cx + ch_r, cy))
        p.drawLine(QPointF(cx, cy - ch_r), QPointF(cx, cy - gap_h))
        p.drawLine(QPointF(cx, cy + gap_h), QPointF(cx, cy + ch_r))

        bl = 28
        bc = qcol(C.GOLD, 180)
        hl, hr = cx - fw / 2, cx + fw / 2
        ht, hb = cy - fw / 2, cy + fw / 2
        p.setPen(QPen(bc, 1.5))
        for bx, by, dx, dy in [(hl, ht, 1, 1), (hr, ht, -1, 1), (hl, hb, 1, -1), (hr, hb, -1, -1)]:
            p.drawLine(QPointF(bx, by), QPointF(bx + dx * bl, by))
            p.drawLine(QPointF(bx, by), QPointF(bx, by + dy * bl))

        orb_r = int(fw * 0.27 * self._scale)
        oc = (200, 0, 50) if self.muted else (0, 60, 110)
        for i in range(8, 0, -1):
            r2 = int(orb_r * i / 8)
            frc = i / 8
            a = max(0, min(255, int(self._halo * 1.1 * frc)))
            p.setBrush(QBrush(QColor(int(oc[0] * frc), int(oc[1] * frc), int(oc[2] * frc), a)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(cx - r2, cy - r2, r2 * 2, r2 * 2))
        p.setPen(QPen(qcol(pri, min(255, int(self._halo * 2))), 1))
        p.setFont(QFont(FONT_HUD, 13, QFont.Weight.Bold))
        p.drawText(QRectF(cx - 80, cy - 14, 160, 28), Qt.AlignmentFlag.AlignCenter, "EMO")

        for pt in self._particles:
            a = max(0, min(255, int(pt[4] * 255)))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(qcol(pri, a)))
            p.drawEllipse(QPointF(pt[0], pt[1]), 2.5, 2.5)

        sy = cy + fw * 0.40
        if self.muted:
            txt, col = "⊘  MUTED", qcol(C.MUTED_C)
        elif self.speaking:
            txt, col = "●  SPEAKING", qcol(C.ACC)
        elif self.state == "THINKING":
            sym = "◈" if self._blink else "◇"
            txt, col = f"{sym}  THINKING", qcol(C.ACC2)
        elif self.state == "LISTENING":
            sym = "●" if self._blink else "○"
            txt, col = f"{sym}  LISTENING", qcol(C.GREEN)
        else:
            sym = "●" if self._blink else "○"
            txt, col = f"{sym}  {self.state}", qcol(pri)
        p.setPen(QPen(col, 1))
        p.setFont(QFont(FONT_HUD, 10, QFont.Weight.Bold))
        p.drawText(QRectF(0, sy, w, 26), Qt.AlignmentFlag.AlignCenter, txt)

        wy = sy + 30
        n, bw = 36, 8
        wx0 = (w - n * bw) / 2
        for i in range(n):
            if self.muted:
                hgt, cl = 2, qcol(C.MUTED_C)
            elif self.speaking:
                hgt = random.randint(3, 20)
                cl = qcol(pri) if hgt > 12 else qcol(C.PRI_DIM)
            else:
                hgt = int(3 + 2 * math.sin(self._tick * 0.09 + i * 0.6))
                cl = qcol(C.BORDER_B)
            p.fillRect(QRectF(wx0 + i * bw, wy + 20 - hgt, bw - 1, hgt), cl)


class HudBubbleWidget(QWidget):
    """Bulle compacte pour overlay vocal (coin écran)."""

    exit_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(220, 220)
        self.state = "LISTENING"
        self.speaking = False
        self.muted = False
        self._tick = 0
        self._rings = [0.0, 120.0, 240.0]
        self._scan = 0.0
        self._scan2 = 180.0
        self._halo = 55.0
        self._tgt_halo = 55.0
        self._blink = True
        self._blink_tick = 0
        self._pulses: list[float] = []
        self._last_t = time.time()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self._timer.start(40)

    def set_state(self, state: str) -> None:
        self.state = state
        self.speaking = state == "SPEAKING"
        self.muted = state == "MUTED"
        self.update()

    def _step(self) -> None:
        self._tick += 1
        now = time.time()
        if now - self._last_t > (0.1 if self.speaking else 0.45):
            self._tgt_halo = (
                random.uniform(130, 175) if self.speaking
                else random.uniform(12, 24) if self.muted
                else random.uniform(45, 68)
            )
            self._last_t = now
        self._halo += (self._tgt_halo - self._halo) * (0.35 if self.speaking else 0.14)
        speeds = [1.4, -0.95, 2.1] if self.speaking else [0.5, -0.32, 0.85]
        for i, spd in enumerate(speeds):
            self._rings[i] = (self._rings[i] + spd) % 360
        self._scan = (self._scan + (2.8 if self.speaking else 1.1)) % 360
        self._scan2 = (self._scan2 + (-1.8 if self.speaking else -0.7)) % 360
        self._pulses = [r + (3.8 if self.speaking else 1.8) for r in self._pulses if r < 148]
        if len(self._pulses) < 2 and random.random() < (0.06 if self.speaking else 0.02):
            self._pulses.append(0.0)
        self._blink_tick += 1
        if self._blink_tick >= 34:
            self._blink = not self._blink
            self._blink_tick = 0
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        fw = min(w, h)
        pri = C.MUTED_C if self.muted else C.PRI
        for i in range(8):
            r = fw * 0.46 * (1.0 - i * 0.08)
            a = max(0, min(255, int(self._halo * 0.06 * (1.0 - i / 8))))
            p.setPen(QPen(qcol(C.GOLD if i % 3 == 0 else pri, a), 1.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))
        for idx, (r_frac, w_r, arc_l, gap) in enumerate([(0.44, 2.5, 110, 72), (0.36, 1.8, 72, 50), (0.28, 1.2, 50, 36)]):
            ring_r = fw * r_frac
            base = self._rings[idx]
            rect = QRectF(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2)
            p.setPen(QPen(qcol(pri, int(self._halo * (1.0 - idx * 0.2))), w_r))
            angle = base
            while angle < base + 360:
                p.drawArc(rect, int(angle * 16), int(arc_l * 16))
                angle += arc_l + gap
        orb_r = int(fw * 0.22)
        for i in range(6, 0, -1):
            r2 = int(orb_r * i / 6)
            frc = i / 6
            a = max(0, min(255, int(self._halo * frc * 0.9)))
            p.setBrush(QBrush(QColor(0, int(55 * frc), int(100 * frc), a)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(cx - r2, cy - r2, r2 * 2, r2 * 2))
        p.setPen(QPen(qcol(pri, min(255, int(self._halo * 2))), 1))
        p.setFont(QFont(FONT_HUD, 11, QFont.Weight.Bold))
        p.drawText(QRectF(cx - 60, cy - 12, 120, 24), Qt.AlignmentFlag.AlignCenter, "EMO")
        if self.state == "LISTENING":
            sym = "●" if self._blink else "○"
            txt, col = f"{sym}  LISTENING", qcol(C.GREEN)
        elif self.speaking:
            txt, col = "SPEAKING", qcol(C.ACC)
        elif self.state == "THINKING":
            txt, col = "THINKING", qcol(C.ACC2)
        else:
            txt, col = self.state, qcol(pri)
        p.setFont(QFont(FONT_HUD, 8, QFont.Weight.Bold))
        p.setPen(QPen(col, 1))
        p.drawText(QRectF(0, cy + fw * 0.30, w, 20), Qt.AlignmentFlag.AlignCenter, txt)
