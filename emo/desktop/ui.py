"""Interface PyQt6 — style MARK XLVIII (bulle HUD, SYS, journal)."""
from __future__ import annotations

import asyncio
import platform
import sys
import time
import webbrowser
from pathlib import Path
from typing import Any

try:
    from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal, QUrl
    from PyQt6.QtGui import QFont, QKeySequence, QShortcut, QDragEnterEvent, QDropEvent
    from PyQt6.QtWidgets import (
        QApplication,
        QDialog,
        QDialogButtonBox,
        QFormLayout,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QMainWindow,
        QPushButton,
        QSizePolicy,
        QSplitter,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    print("PyQt6 requis: pip install PyQt6", file=sys.stderr)
    sys.exit(1)

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore

from emo.desktop.actions.skill_loader import list_skills, run_skill
from emo.desktop.brain.agent_brain import AgentBrain, BrainStep
from emo.desktop.brain.dev_agent import DevAgent
from emo.desktop.cloud_client import CloudClient
from emo.desktop.config import load_config, save_config
from emo.desktop.dashboard.server import DashboardServer, broadcast_log, dashboard_local_url, site_link_url
from emo.desktop.dashboard.server import _get_pair_code, set_live_session, set_wake_handler
from emo.desktop.gemini_session import GeminiSession
from emo.desktop.hud_widget import (
    C,
    FONT_HUD,
    HudBubbleWidget,
    HudCanvas,
    JournalWidget,
    MetricBar,
    _LEFT_W,
    _RIGHT_W,
    app_stylesheet,
    btn_style,
)
from emo.desktop.memory import append_journal
from emo.desktop.core.live_session import EmoLiveSession
from emo.desktop.mode_switch import parse_mode_switch
from emo.desktop.relay import start_relay_from_env
from emo.desktop.system_monitor import SystemMonitor
from emo.desktop.task_router import route_message
from emo.desktop.tts import EmoSpeechEngine

_OS = platform.system()
_BOOT = time.time()


class AsyncWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, coro_factory, parent=None):
        super().__init__(parent)
        self._coro_factory = coro_factory

    def run(self):
        try:
            result = asyncio.run(self._coro_factory())
            self.finished.emit(str(result))
        except Exception as e:
            self.error.emit(str(e))


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Paramètres — Émo Desktop")
        cfg = load_config()
        layout = QFormLayout(self)
        self.gemini = QLineEdit(cfg.get("gemini_api_key", ""))
        self.openai = QLineEdit(cfg.get("openai_api_key", ""))
        self.backend = QLineEdit(cfg.get("backend_url", "https://xroxx-emo-online-api.hf.space"))
        self.email = QLineEdit(cfg.get("user_email", ""))
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Mot de passe Emo Online")
        self.session = QLineEdit(cfg.get("session_token", ""))
        self.token = QLineEdit(cfg.get("agent_token", ""))
        self.port = QLineEdit(str(cfg.get("dashboard_port", 8000)))
        self.agent_folder = QLineEdit(cfg.get("agent_folder", ""))
        self.camera_index = QLineEdit(str(cfg.get("camera_index", 0)))
        for w in (self.gemini, self.openai, self.session, self.token):
            w.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("Gemini API", self.gemini)
        layout.addRow("OpenAI API", self.openai)
        layout.addRow("Backend URL", self.backend)
        layout.addRow("Email Emo Online", self.email)
        layout.addRow("Mot de passe", self.password)
        self._connect_btn = QPushButton("Connecter via Emo Online")
        self._connect_btn.clicked.connect(self._do_connect)
        layout.addRow(self._connect_btn)
        self._site_btn = QPushButton("Ouvrir le site (appairage)")
        self._site_btn.clicked.connect(self._open_site_pairing)
        layout.addRow(self._site_btn)
        layout.addRow("Session token", self.session)
        layout.addRow("Agent token", self.token)
        layout.addRow("Dashboard port", self.port)
        layout.addRow("Dossier agent", self.agent_folder)
        layout.addRow("Index caméra", self.camera_index)
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 8pt;")
        layout.addRow(self._status_lbl)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        self._cloud = CloudClient()

    def _do_connect(self) -> None:
        email = self.email.text().strip()
        password = self.password.text().strip()
        if not email or not password:
            self._status_lbl.setText("Email et mot de passe requis.")
            return
        self._connect_btn.setEnabled(False)
        self._status_lbl.setText("Connexion…")
        cloud = self._cloud

        async def _connect():
            r = await cloud.login(email, password)
            if r.get("ok"):
                return f"OK|{r.get('email', email)}"
            return f"ERR|{r.get('error', 'Échec')}"

        worker = AsyncWorker(_connect, parent=self)

        def _ok(result: str):
            self._connect_btn.setEnabled(True)
            if result.startswith("OK|"):
                cfg = load_config()
                self.session.setText(cfg.get("session_token", ""))
                self.token.setText(cfg.get("agent_token", ""))
                self._status_lbl.setText(f"Connecté : {result.split('|', 1)[-1]}")
            else:
                self._status_lbl.setText(result.split("|", 1)[-1][:120])

        worker.finished.connect(_ok)
        worker.error.connect(
            lambda e: (self._connect_btn.setEnabled(True), self._status_lbl.setText(str(e)))
        )
        worker.start()
        self._connect_worker = worker

    def _open_site_pairing(self) -> None:
        parent = self.parent()
        if parent and hasattr(parent, "_connect_via_site"):
            parent._connect_via_site()

    def closeEvent(self, event) -> None:
        worker = getattr(self, "_connect_worker", None)
        if worker and worker.isRunning():
            worker.wait(3000)
        super().closeEvent(event)

    def values(self) -> dict:
        return {
            "gemini_api_key": self.gemini.text().strip(),
            "openai_api_key": self.openai.text().strip(),
            "backend_url": self.backend.text().strip(),
            "user_email": self.email.text().strip(),
            "session_token": self.session.text().strip(),
            "agent_token": self.token.text().strip(),
            "dashboard_port": int(self.port.text() or "8000"),
            "agent_folder": self.agent_folder.text().strip(),
            "camera_index": int(self.camera_index.text() or "0"),
        }


class VoiceOverlay(QWidget):
    """Overlay vocal compact — bulle HUD coin écran (Mark-XLVIII)."""

    exit_requested = pyqtSignal()

    _W, _MIN_H = 280, 340

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedWidth(self._W)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 12)
        lay.setSpacing(6)
        self.bubble = HudBubbleWidget(self)
        lay.addWidget(self.bubble, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.user_lbl = QLabel("Vous: …")
        self.user_lbl.setWordWrap(True)
        self.user_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        self.user_lbl.setFont(QFont(FONT_HUD, 8))
        lay.addWidget(self.user_lbl)
        self.emo_lbl = QLabel("Émo: …")
        self.emo_lbl.setWordWrap(True)
        self.emo_lbl.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        self.emo_lbl.setFont(QFont(FONT_HUD, 8))
        lay.addWidget(self.emo_lbl)
        hint = QLabel("double-clic · quitter")
        hint.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 7pt;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(hint)

    def set_state(self, state: str) -> None:
        self.bubble.set_state(state)

    def set_user_text(self, text: str) -> None:
        t = (text or "").strip()
        self.user_lbl.setText(f"Vous: {t[:80]}" if t else "Vous: …")
        self._reflow()

    def set_emo_text(self, text: str) -> None:
        t = (text or "").strip()
        self.emo_lbl.setText(f"Émo: {t[:120]}" if t else "Émo: …")
        self._reflow()

    def _reflow(self) -> None:
        self.adjustSize()
        h = max(self._MIN_H, self.sizeHint().height())
        self.setFixedHeight(h)
        self.position_top_right()

    def position_top_right(self) -> None:
        screen = QApplication.primaryScreen()
        if not screen:
            self.move(100, 40)
            return
        geo = screen.availableGeometry()
        self.move(geo.right() - self.width() - 18, geo.top() + 14)

    def show_overlay(self) -> None:
        self.position_top_right()
        self.show()
        self.raise_()

    def mouseDoubleClickEvent(self, event):
        self.exit_requested.emit()
        event.accept()


class EmoMainWindow(QMainWindow):
    _stt_transcript = pyqtSignal(str)
    _stt_partial = pyqtSignal(str)
    _live_assistant = pyqtSignal(str)
    _live_log = pyqtSignal(str)
    _hud_state_sig = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Émo — MARK XLVIII")
        self.resize(980, 700)
        self.setMinimumSize(820, 580)
        self._muted = False
        self._worker: AsyncWorker | None = None
        self._voice_gen = 0
        self._status_worker: AsyncWorker | None = None
        self._sync_worker: AsyncWorker | None = None
        self._synced_message_ids: set[str] = set()
        self._mode = "CHAT"
        self._explorer_root = Path.home()
        self._current_file = ""
        self._voice_overlay = VoiceOverlay()
        self._voice_overlay.hide()
        self._live: EmoLiveSession | None = None
        self._voice_queue: list[str] = []
        self._cloud = CloudClient(on_log=self._journal)

        self._build_ui()
        self.setStyleSheet(app_stylesheet())
        self._bind_shortcuts()
        self._stt_transcript.connect(self._on_stt_transcript)
        self._stt_partial.connect(self._on_stt_partial)
        self._live_assistant.connect(self._on_live_assistant)
        self._live_log.connect(self._journal)
        self._hud_state_sig.connect(self._set_hud_state)
        self._voice_overlay.exit_requested.connect(self._on_voice_overlay_exit)

        cfg = load_config()
        paired = bool((cfg.get("session_token") or "").strip())
        agent_folder = str(cfg.get("agent_folder") or "").strip()
        self.gemini = GeminiSession(on_log=lambda m: self._live_log.emit(m))
        # Charon via EmoLiveSession uniquement — pas de 2e session Live TTS.
        self.tts = EmoSpeechEngine(
            on_speaking_start=lambda: self._hud_state_sig.emit("SPEAKING"),
            on_speaking_end=lambda: self._hud_state_sig.emit("MUTED" if self._muted else "LISTENING"),
            on_log=lambda m: self._live_log.emit(m),
            prefer_local=True,
        )
        self.tts.start()
        self._live = EmoLiveSession(
            on_log=lambda m: self._live_log.emit(m),
            on_user_speech=lambda t: self._stt_transcript.emit(t),
            on_assistant_speech=lambda t: self._live_assistant.emit(t),
            on_state=lambda s: self._hud_state_sig.emit(s),
            is_muted=lambda: self._muted,
            cloud_hybrid=paired,
            agent_folder=agent_folder,
            current_file=lambda: self._current_file,
        )
        self._live.start()
        set_live_session(self._live)
        set_wake_handler(self._wake_from_dashboard)
        self.dev_agent = DevAgent(on_log=self._journal)
        self.brain = AgentBrain(
            on_step=self._on_brain_step,
            run_skill=self._run_skill_sync,
            run_dev=self._run_dev_sync,
            chat=self._chat_async,
        )

        self.monitor = SystemMonitor(interval=2.0, on_update=self._on_stats)
        self.monitor.start()

        self.relay = start_relay_from_env(on_status=self._journal)
        cfg = load_config()
        port = int(cfg.get("dashboard_port") or 8000)
        self.dashboard = DashboardServer(
            port=port,
            command_handler=self._handle_mobile_command,
            pair_handler=self._on_paired_from_browser,
            wake_handler=lambda: self._hud_state_sig.emit("LISTENING"),
            phone_audio_handler=self._on_phone_audio,
        )
        self.dashboard.start()
        pair_url = dashboard_local_url(port)
        self._journal(f"SYS: Dashboard {pair_url} (LAN: port {port})")

        QTimer.singleShot(500, self._check_cloud_status)
        QTimer.singleShot(1500, self._sync_cloud_history)
        cfg = load_config()
        if not (cfg.get("session_token") or "").strip():
            QTimer.singleShot(2000, self._connect_via_site)

        self._heartbeat_tmr = QTimer(self)
        self._heartbeat_tmr.timeout.connect(self._send_desktop_heartbeat)
        self._heartbeat_tmr.start(30000)

        self._clock_tmr = QTimer(self)
        self._clock_tmr.timeout.connect(self._tick_clock)
        self._clock_tmr.start(1000)
        self._tick_clock()
        self._refresh_explorer()
        self._set_hud_state("LISTENING")

    def _build_ui(self):
        central = QWidget()
        central.setStyleSheet("background: transparent;")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_left_panel())
        body.addWidget(self._build_center(), stretch=5)
        body.addWidget(self._build_right_panel())
        root.addLayout(body, stretch=1)
        root.addWidget(self._build_footer())

    def _build_header(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(40)
        w.setStyleSheet(f"background: transparent; border-bottom: 1px solid {C.BORDER};")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(14, 0, 14, 0)
        brand = QLabel("◈  ÉMO")
        brand.setFont(QFont(FONT_HUD, 11, QFont.Weight.Bold))
        brand.setStyleSheet(f"color: {C.PRI}; background: transparent; letter-spacing: 3px;")
        lay.addWidget(brand)
        lay.addStretch()
        self._mode_lbl = QLabel("CHAT")
        self._mode_lbl.setFont(QFont(FONT_HUD, 7))
        self._mode_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        lay.addWidget(self._mode_lbl)
        lay.addSpacing(12)
        self._clock_lbl = QLabel("00:00")
        self._clock_lbl.setFont(QFont(FONT_HUD, 10))
        self._clock_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        lay.addWidget(self._clock_lbl)
        lay.addSpacing(10)
        self._voice_btn = QPushButton("VOCAL")
        self._voice_btn.setFixedSize(58, 22)
        self._voice_btn.setCheckable(True)
        self._voice_btn.setStyleSheet(btn_style(C.PRI_DIM))
        self._voice_btn.toggled.connect(self._toggle_voice_mode)
        lay.addWidget(self._voice_btn)
        self._agent_btn = QPushButton("AGENT")
        self._agent_btn.setFixedSize(58, 22)
        self._agent_btn.setCheckable(True)
        self._agent_btn.setStyleSheet(btn_style(C.TEXT_DIM, gold=True))
        self._agent_btn.toggled.connect(self._toggle_agent_mode)
        lay.addWidget(self._agent_btn)
        return w

    def _build_left_panel(self) -> QWidget:
        w = QWidget()
        w.setFixedWidth(_LEFT_W)
        w.setStyleSheet(f"background: transparent; border-right: 1px solid {C.BORDER};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 10, 8, 10)
        lay.setSpacing(6)
        hdr = QLabel("SYS")
        hdr.setFont(QFont(FONT_HUD, 7))
        hdr.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        lay.addWidget(hdr)
        self._bar_cpu = MetricBar("CPU", C.PRI)
        self._bar_mem = MetricBar("MEM", C.ACC2)
        self._bar_net = MetricBar("NET", C.GREEN)
        self._bar_gpu = MetricBar("GPU", C.ACC)
        for bar in (self._bar_cpu, self._bar_mem, self._bar_net, self._bar_gpu):
            lay.addWidget(bar)
        info = QWidget()
        info.setStyleSheet(f"background: {C.PANEL2}; border: 1px solid {C.BORDER};")
        ip = QVBoxLayout(info)
        ip.setContentsMargins(6, 5, 6, 5)
        self._uptime_lbl = QLabel("UP  --:--")
        self._uptime_lbl.setFont(QFont(FONT_HUD, 8, QFont.Weight.Bold))
        self._uptime_lbl.setStyleSheet(f"color: {C.GREEN}; background: transparent;")
        ip.addWidget(self._uptime_lbl)
        self._proc_lbl = QLabel("PROC  --")
        self._proc_lbl.setFont(QFont(FONT_HUD, 8))
        self._proc_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        ip.addWidget(self._proc_lbl)
        os_name = {"Windows": "WIN", "Darwin": "macOS", "Linux": "LINUX"}.get(_OS, _OS.upper())
        ip.addWidget(QLabel(f"OS  {os_name}"))
        lay.addWidget(info)
        lay.addStretch()
        return w

    def _build_center(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        self.hud = HudCanvas()
        self.hud.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._agent_panel = QWidget()
        self._agent_panel.hide()
        ap = QVBoxLayout(self._agent_panel)
        ap.setContentsMargins(12, 8, 12, 8)
        ap.addWidget(QLabel("◈  AGENT — explorateur"))
        self.explorer = QListWidget()
        ap.addWidget(self.explorer, stretch=1)
        btn_row = QHBoxLayout()
        for label, slot in (("Dossier", self._btn_dossier), ("Analyser", self._btn_analyser), ("Exécuter", self._btn_executer)):
            b = QPushButton(label)
            b.setStyleSheet(btn_style(C.PRI_DIM))
            b.clicked.connect(slot)
            btn_row.addWidget(b)
        ap.addLayout(btn_row)
        split = QSplitter(Qt.Orientation.Vertical)
        split.setStyleSheet(f"QSplitter::handle {{ background: {C.BORDER}; height: 3px; }}")
        split.addWidget(self.hud)
        split.addWidget(self._agent_panel)
        split.setStretchFactor(0, 4)
        split.setStretchFactor(1, 1)
        lay.addWidget(split, stretch=1)
        return w

    def _build_right_panel(self) -> QWidget:
        w = QWidget()
        w.setFixedWidth(_RIGHT_W)
        w.setStyleSheet(f"background: transparent; border-left: 1px solid {C.BORDER};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        def sec(txt: str) -> QLabel:
            l = QLabel(txt)
            l.setFont(QFont(FONT_HUD, 7))
            l.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
            return l

        lay.addWidget(sec("journal"))
        self.journal = JournalWidget()
        self.journal.setReadOnly(True)
        self.journal.setAcceptDrops(True)
        self.journal.dragEnterEvent = self._journal_drag_enter  # type: ignore[method-assign]
        self.journal.dropEvent = self._journal_drop  # type: ignore[method-assign]
        lay.addWidget(self.journal, stretch=1)
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER};")
        lay.addWidget(sep)
        lay.addWidget(sec("commande"))
        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Commande…")
        self.input.setFixedHeight(26)
        self.input.returnPressed.connect(self._on_submit)
        row.addWidget(self.input)
        send = QPushButton("→")
        send.setFixedSize(26, 26)
        send.setStyleSheet(btn_style(C.PRI))
        send.clicked.connect(self._on_submit)
        row.addWidget(send)
        lay.addLayout(row)
        ctrl = QHBoxLayout()
        stop = QPushButton("stop")
        stop.setStyleSheet(btn_style(C.MUTED_C))
        stop.clicked.connect(self._interrupt)
        ctrl.addWidget(stop)
        self._mute_btn = QPushButton("micro")
        self._mute_btn.clicked.connect(self._toggle_mute)
        ctrl.addWidget(self._mute_btn)
        link = QPushButton("link")
        link.setStyleSheet(btn_style(C.PRI_DIM))
        link.setToolTip("Connecter via Emo Online (ouvre le site)")
        link.clicked.connect(self._connect_via_site)
        ctrl.addWidget(link)
        settings = QPushButton("⚙")
        settings.setFixedSize(24, 24)
        settings.setStyleSheet(btn_style(C.TEXT_DIM))
        settings.clicked.connect(self._open_settings)
        ctrl.addWidget(settings)
        lay.addLayout(ctrl)
        skills = QLabel(f"{len(list_skills())} skills")
        skills.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 7pt;")
        lay.addWidget(skills)
        return w

    def _build_footer(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(18)
        w.setStyleSheet(f"background: transparent; border-top: 1px solid {C.BORDER};")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(12, 0, 12, 0)
        hint = QLabel("F4 mute · F11 plein écran · ESC stop")
        hint.setFont(QFont(FONT_HUD, 6))
        hint.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        lay.addWidget(hint)
        return w

    def _bind_shortcuts(self):
        QShortcut(QKeySequence("F4"), self, self._toggle_mute)
        QShortcut(QKeySequence("F11"), self, self._toggle_fullscreen)
        QShortcut(QKeySequence("Escape"), self, self._interrupt)

    def _tick_clock(self):
        self._clock_lbl.setText(time.strftime("%H:%M"))
        up = int(time.time() - _BOOT)
        self._uptime_lbl.setText(f"UP  {up // 60:02d}:{up % 60:02d}")
        if psutil:
            self._proc_lbl.setText(f"PROC  {len(psutil.pids())}")

    def _set_hud_state(self, state: str) -> None:
        self.hud.set_state(state)
        if self._voice_overlay.isVisible():
            self._voice_overlay.set_state(state)

    def _on_voice_overlay_exit(self) -> None:
        if self._voice_btn.isChecked():
            self._voice_btn.setChecked(False)

    def _wake_from_dashboard(self) -> None:
        if self._live:
            self._live.set_phone_active(False)
        self._hud_state_sig.emit("LISTENING")

    def _journal_drag_enter(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _journal_drop(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if not urls:
            return
        path = urls[0].toLocalFile()
        if path:
            self._set_uploaded_file(path)
        event.acceptProposedAction()

    def _set_uploaded_file(self, path: str) -> None:
        p = Path(path)
        if not p.is_file():
            return
        self._current_file = str(p.resolve())
        self._journal(f"SYS: Fichier chargé — {p.name}")

    def _pick_file_for_processor(self) -> None:
        from PyQt6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(self, "Choisir un fichier")
        if path:
            self._set_uploaded_file(path)

    def _on_phone_audio(self, active: bool, _data: bytes | None = None) -> None:
        if self._live:
            self._live.set_phone_active(bool(active))

    def _journal(self, text: str) -> None:
        journal = getattr(self, "journal", None)
        if journal is not None:
            journal.append_line(text)
        append_journal(text)
        try:
            broadcast_log(text)
        except Exception:
            pass

    def _on_stats(self, stats) -> None:
        self._bar_cpu.set_value(stats.cpu_percent, f"{stats.cpu_percent:.0f}%")
        self._bar_mem.set_value(stats.ram_percent, f"{stats.ram_percent:.0f}%")
        if psutil:
            try:
                nc = psutil.net_io_counters()
                net_kb = (getattr(nc, "bytes_sent", 0) + getattr(nc, "bytes_recv", 0)) % 100000 / 1024
                self._bar_net.set_value(min(100, net_kb / 10), f"{net_kb:.0f}KB/s")
            except Exception:
                self._bar_net.set_value(0, "0KB/s")
        self._bar_gpu.set_value(0, "N/A")

    def _set_mode(self, mode: str) -> str:
        mode = (mode or "").upper()
        labels = {
            "CHAT": "discussion texte",
            "VOCAL": "vocal — micro actif",
            "AGENT": "agent — planification et outils",
        }
        if mode not in labels:
            return "Mode inconnu. Utilisez CHAT, VOCAL ou AGENT."

        if self._mode == mode:
            return f"Déjà en mode {mode} ({labels[mode]})."

        if mode == "CHAT":
            if self._voice_btn.isChecked():
                self._voice_btn.setChecked(False)
            elif self._agent_btn.isChecked():
                self._agent_btn.setChecked(False)
            else:
                self._mode = "CHAT"
                self._mode_lbl.setText("CHAT")
        elif mode == "VOCAL":
            if self._agent_btn.isChecked():
                self._agent_btn.setChecked(False)
            if not self._voice_btn.isChecked():
                self._voice_btn.setChecked(True)
        elif mode == "AGENT":
            if not self._agent_btn.isChecked():
                self._agent_btn.setChecked(True)

        return f"Mode {mode} — {labels[mode]}."

    def _try_mode_switch(self, text: str) -> bool:
        target = parse_mode_switch(text)
        if not target:
            return False
        if target == "STATUS":
            labels = {
                "CHAT": "discussion texte",
                "VOCAL": "vocal — micro actif",
                "AGENT": "agent — planification et outils",
            }
            msg = f"Mode actuel : {self._mode} ({labels.get(self._mode, '')})."
        else:
            msg = self._set_mode(target)
        self._journal(f"Émo: {msg}")
        if self._voice_overlay and self._voice_overlay.isVisible():
            self._voice_overlay.set_emo_text(msg)
        return True

    def _is_paired(self) -> bool:
        return bool((load_config().get("session_token") or "").strip())

    def _speak_response(self, text: str) -> None:
        """Charon via Live quand possible ; repli edge-tts/pyttsx3 sinon."""
        text = (text or "").strip()
        if not text or self._muted:
            return
        if self._live and self._live.session:
            self._live.speak(text)
        elif self.tts:
            self.tts.speak(text)

    def _toggle_voice_mode(self, on: bool) -> None:
        try:
            if on:
                if self._agent_btn.isChecked():
                    self._agent_btn.blockSignals(True)
                    self._agent_btn.setChecked(False)
                    self._agent_btn.blockSignals(False)
                    self._toggle_agent_mode(False)
                self._mode = "VOCAL"
                self._mode_lbl.setText("VOCAL")
                self._voice_overlay.set_user_text("")
                self._voice_overlay.set_emo_text("")
                self._voice_overlay.set_state(self.hud.state)
                self._voice_overlay.show_overlay()
                self._journal("SYS: Overlay vocal actif (coin haut-droit).")
                self._set_hud_state("MUTED" if self._muted else "LISTENING")
            else:
                self._mode = "CHAT"
                self._mode_lbl.setText("CHAT")
                self._voice_overlay.hide()
                self._journal("SYS: Mode vocal désactivé.")
                self._set_hud_state("MUTED" if self._muted else "LISTENING")
        except Exception as e:
            self._journal(f"ERR: Mode vocal — {e}")

    def _on_live_assistant(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        if self._live and self._live.cloud_hybrid:
            return
        self._journal(f"Émo: {text}")
        if self._voice_overlay.isVisible():
            self._voice_overlay.set_emo_text(text)

    def _pump_voice_queue(self) -> None:
        if not self._voice_queue:
            return
        if self._worker and self._worker.isRunning():
            return
        text = self._voice_queue.pop(0)
        gen = self._voice_gen
        self._worker = AsyncWorker(lambda: self._process_chat(text), parent=self)

        def _done(r: str):
            if gen != self._voice_gen:
                QTimer.singleShot(100, self._pump_voice_queue)
                return
            self._journal(f"Émo: {r}")
            if self._voice_overlay.isVisible():
                self._voice_overlay.set_emo_text(r)
            if not self._muted:
                self._speak_response(r)
            QTimer.singleShot(100, self._pump_voice_queue)

        self._worker.finished.connect(_done)
        self._worker.error.connect(lambda e: self._journal(f"Erreur: {e}"))
        self._worker.start()

    def _on_stt_partial(self, text: str) -> None:
        if self._voice_overlay.isVisible():
            self._voice_overlay.set_user_text(text)

    def _on_stt_transcript(self, text: str) -> None:
        text = (text or "").strip()
        if not text or self._muted:
            return
        self._journal(f"Vous: {text}")
        if self._voice_overlay.isVisible():
            self._voice_overlay.set_user_text(text)
        if self._try_mode_switch(text):
            return
        if self._live and not self._live.cloud_hybrid:
            return
        self.tts.interrupt()
        if self._live:
            self._live.interrupt()
        if self._worker and self._worker.isRunning():
            self._journal("SYS: Interruption — nouvelle commande vocale.")
        self._voice_gen += 1
        gen = self._voice_gen
        self._worker = AsyncWorker(lambda: self._process_chat(text), parent=self)

        def _done(r: str):
            if gen != self._voice_gen:
                return
            self._journal(f"Émo: {r}")
            if self._voice_overlay.isVisible():
                self._voice_overlay.set_emo_text(r)
            if not self._muted:
                self._speak_response(r)

        self._worker.finished.connect(_done)
        self._worker.error.connect(lambda e: self._journal(f"Erreur: {e}"))
        self._worker.start()

    def _toggle_agent_mode(self, on: bool) -> None:
        try:
            if on:
                if self._voice_btn.isChecked():
                    self._voice_btn.blockSignals(True)
                    self._voice_btn.setChecked(False)
                    self._voice_btn.blockSignals(False)
                    self._voice_overlay.hide()
                self._mode = "AGENT"
                self._mode_lbl.setText("AGENT")
                self._agent_panel.show()
                self._set_hud_state("THINKING")
            else:
                self._mode = "CHAT"
                self._mode_lbl.setText("CHAT")
                self._agent_panel.hide()
                self._set_hud_state("MUTED" if self._muted else "LISTENING")
        except Exception as e:
            self._journal(f"ERR: Mode agent — {e}")

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _on_paired_from_browser(self, source: str) -> None:
        self._journal(f"SYS: Appairage réussi ({source}).")
        muted = self._muted
        self.tts.stop()
        self.tts = EmoSpeechEngine(
            on_speaking_start=lambda: self._hud_state_sig.emit("SPEAKING"),
            on_speaking_end=lambda: self._hud_state_sig.emit("MUTED" if self._muted else "LISTENING"),
            on_log=lambda m: self._live_log.emit(m),
            prefer_local=True,
        )
        self.tts.set_muted(muted)
        self.tts.start()
        if self.relay:
            self.relay.stop()
        self.relay = start_relay_from_env(on_status=lambda m: self._live_log.emit(m))
        self.gemini = GeminiSession(on_log=lambda m: self._live_log.emit(m))
        self._cloud = CloudClient(on_log=lambda m: self._live_log.emit(m))
        if self._live:
            self._live.stop()
        self._live = EmoLiveSession(
            on_log=lambda m: self._live_log.emit(m),
            on_user_speech=lambda t: self._stt_transcript.emit(t),
            on_assistant_speech=lambda t: self._live_assistant.emit(t),
            on_state=lambda s: self._hud_state_sig.emit(s),
            is_muted=lambda: self._muted,
            cloud_hybrid=True,
            agent_folder=str(load_config().get("agent_folder") or ""),
            current_file=lambda: self._current_file,
        )
        self._live.start()
        set_live_session(self._live)
        QTimer.singleShot(300, self._check_cloud_status)
        QTimer.singleShot(800, self._sync_cloud_history)

    def _connect_via_site(self) -> None:
        cfg = load_config()
        port = int(cfg.get("dashboard_port") or 8000)
        code = _get_pair_code()
        url = site_link_url(code, port)
        self._journal(f"SYS: Ouvrez le site pour confirmer → {url}")
        try:
            webbrowser.open(url)
        except Exception as e:
            self._journal(f"ERR: Impossible d'ouvrir le navigateur — {e}")
            return
        self._poll_pair_claim(code)

    def _poll_pair_claim(self, code: str) -> None:
        if getattr(self, "_pair_worker", None) and self._pair_worker.isRunning():
            self._journal("SYS: Appairage déjà en cours…")
            return
        cloud = self._cloud

        async def _poll():
            for _ in range(90):
                r = await cloud.poll_pair_claim(code)
                if r.get("ok"):
                    return f"OK|{r.get('email', '')}"
                if r.get("error"):
                    return f"ERR|{r['error']}"
                await asyncio.sleep(2)
            return "ERR|Délai dépassé — réessayez depuis le site"

        worker = AsyncWorker(_poll, parent=self)
        self._pair_worker = worker

        def _done(raw: str):
            if raw.startswith("OK|"):
                self._on_paired_from_browser("site")
                self._journal(f"SYS: Compte lié — {raw.split('|', 1)[-1]}")
            else:
                self._journal(f"ERR: {raw.split('|', 1)[-1]}")

        worker.finished.connect(_done)
        worker.error.connect(lambda e: self._journal(f"ERR: {e}"))
        worker.start()

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            save_config(dlg.values())
            self._journal("SYS: Paramètres enregistrés.")
            self.gemini = GeminiSession(on_log=self._journal)
            self._cloud = CloudClient(on_log=self._journal)
            self.tts.stop()
            self.tts = EmoSpeechEngine(
                on_speaking_start=lambda: self._set_hud_state("SPEAKING"),
                on_speaking_end=lambda: self._set_hud_state("MUTED" if self._muted else "LISTENING"),
                on_log=self._journal,
                prefer_local=True,
            )
            self.tts.set_muted(self._muted)
            self.tts.start()
            self.relay = start_relay_from_env(on_status=self._journal)
            QTimer.singleShot(300, self._check_cloud_status)

    def _send_desktop_heartbeat(self) -> None:
        if not (load_config().get("session_token") or "").strip():
            return
        cloud = self._cloud

        async def _hb():
            return await cloud.send_heartbeat()

        worker = AsyncWorker(_hb, parent=self)
        worker.start()

    def _check_cloud_status(self) -> None:
        if getattr(self, "_status_worker", None) and self._status_worker.isRunning():
            return
        cloud = self._cloud

        async def _status():
            st = await cloud.sync_status()
            return (
                f"{int(bool(st.get('cloud_ok')))}|"
                f"{int(bool(st.get('desktop_online')))}|"
                f"{int(bool(st.get('agent_online')))}|"
                f"{st.get('email') or 'non connecté'}"
            )

        worker = AsyncWorker(_status, parent=self)
        self._status_worker = worker

        def _done(raw: str):
            parts = raw.split("|", 3)
            if len(parts) < 4:
                return
            cloud_s = "OK" if parts[0] == "1" else "hors ligne"
            desktop_s = "OK" if parts[1] == "1" else "offline"
            tools_s = "OK" if parts[2] == "1" else "offline"
            self._journal(f"SYS: Cloud {cloud_s} · Desktop {desktop_s} · Outils {tools_s} · {parts[3]}")
            if self.gemini.quota_exhausted and not (load_config().get("session_token") or "").strip():
                self._journal(
                    "SYS: Quota Gemini épuisé — mode cloud actif (Paramètres → Connecter)."
                )
            self._status_worker = None

        worker.finished.connect(_done)
        worker.error.connect(lambda _e: setattr(self, "_status_worker", None))
        worker.start()

    def _sync_cloud_history(self) -> None:
        cfg = load_config()
        if not (cfg.get("session_token") or "").strip():
            return
        if getattr(self, "_sync_worker", None) and self._sync_worker.isRunning():
            return
        cloud = self._cloud

        async def _pull():
            msgs = await cloud.pull_messages(20)
            lines = []
            for m in msgs:
                mid = str(m.get("message_id") or m.get("created_at") or "")
                content = (m.get("content") or "")[:200]
                if not content:
                    continue
                if mid and mid in self._synced_message_ids:
                    continue
                if mid:
                    self._synced_message_ids.add(mid)
                role = m.get("role", "user")
                prefix = "Vous" if role == "user" else "Émo"
                lines.append(f"[sync] {prefix}: {content}")
            return "\n".join(lines) if lines else ""

        worker = AsyncWorker(_pull, parent=self)
        self._sync_worker = worker

        def _done(raw: str):
            if not raw:
                self._sync_worker = None
                return
            for line in raw.split("\n"):
                self._journal(line)
            if raw:
                self._journal(f"SYS: {raw.count(chr(10)) + 1} messages cloud synchronisés.")
            self._sync_worker = None

        worker.finished.connect(_done)
        worker.error.connect(lambda _e: setattr(self, "_sync_worker", None))
        worker.start()

    def _toggle_mute(self) -> None:
        self._muted = not self._muted
        self.hud.muted = self._muted
        self.tts.set_muted(self._muted)
        self._mute_btn.setText("mute" if self._muted else "micro")
        self._set_hud_state("MUTED" if self._muted else "LISTENING")
        self._journal("SYS: Micro coupé." if self._muted else "SYS: Micro actif.")

    def _interrupt(self) -> None:
        self.brain.interrupt()
        if self._live:
            self._live.interrupt()
        self.tts.interrupt()
        self._voice_gen += 1
        self._voice_queue.clear()
        self._set_hud_state("LISTENING")
        self._journal("SYS: Interrompu.")

    def _refresh_explorer(self) -> None:
        self.explorer.clear()
        try:
            for entry in sorted(self._explorer_root.iterdir())[:200]:
                prefix = "📁 " if entry.is_dir() else "📄 "
                self.explorer.addItem(prefix + entry.name)
        except OSError as e:
            self.explorer.addItem(f"Erreur: {e}")

    def _btn_dossier(self) -> None:
        items = self.explorer.selectedItems()
        if items:
            name = items[0].text().replace("📁 ", "").replace("📄 ", "")
            p = self._explorer_root / name
            if p.is_dir():
                self._explorer_root = p
        self._refresh_explorer()
        self._journal(f"SYS: Dossier {self._explorer_root}")

    def _btn_analyser(self) -> None:
        from emo.desktop.actions.local_analyzer_skill import run
        r = run({"path": str(self._explorer_root), "action": "project"})
        self._journal(r.get("message", str(r)))

    def _btn_executer(self) -> None:
        items = self.explorer.selectedItems()
        if not items:
            self._journal("SYS: Sélectionnez un fichier.")
            return
        name = items[0].text().replace("📁 ", "").replace("📄 ", "")
        path = self._explorer_root / name
        if path.suffix == ".py":
            from emo.desktop.actions.run_python_script import run
            r = run({"path": str(path)})
        else:
            from emo.desktop.actions.open_app import run
            r = run({"app": str(path)})
        self._journal(r.get("message", str(r)))

    def _run_skill_sync(self, name: str, args: dict) -> Any:
        r = run_skill(name, args)
        return r.get("message") or str(r) if isinstance(r, dict) else str(r)

    def _run_dev_sync(self, prompt: str) -> Any:
        r = self.dev_agent.develop(prompt)
        return r.get("run", {}).get("stdout") or str(r)

    async def _chat_async(self, message: str) -> str:
        return await self.gemini.chat_text(message)

    def _on_brain_step(self, step: BrainStep) -> None:
        self._journal(f"[{step.phase.upper()}] {step.content}")
        if step.phase in ("think", "plan"):
            self._set_hud_state("THINKING")

    async def _process_chat(self, text: str) -> str:
        self._set_hud_state("THINKING")
        if self._mode == "CHAT":
            out = await self.gemini.chat_text(text)
        elif self._mode == "AGENT":
            online = bool(self.relay and self.relay.is_running)
            out = await self.brain.process(text, agent_online=online)
        elif self._mode == "VOCAL":
            if self._muted:
                out = "Micro coupé (F4)."
            else:
                route = route_message(text)
                if route.action == "run_skill" and route.skill:
                    r = run_skill(route.skill, route.args or {})
                    out = r.get("message", str(r)) if isinstance(r, dict) else str(r)
                else:
                    out = await self.gemini.chat_text(text)
        else:
            out = await self.gemini.chat_text(text)
        return out

    def _on_submit(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self._journal(f"Vous: {text}")
        if self._voice_overlay.isVisible():
            self._voice_overlay.set_user_text(text)
        if self._try_mode_switch(text):
            return
        if self._worker and self._worker.isRunning():
            self._journal("SYS: Traitement en cours…")
            return
        self._worker = AsyncWorker(lambda: self._process_chat(text), parent=self)

        def _done(r: str):
            self._journal(f"Émo: {r}")
            if self._voice_overlay.isVisible():
                self._voice_overlay.set_emo_text(r)
            if not self._muted:
                self._speak_response(r)

        self._worker.finished.connect(_done)
        self._worker.error.connect(lambda e: self._journal(f"Erreur: {e}"))
        self._worker.start()

    async def _handle_mobile_command(self, text: str) -> str:
        reply = await self._process_chat(text)
        if not self._muted:
            self._speak_response(reply)
        return reply

    def _wait_worker(self, worker: AsyncWorker | None, timeout_ms: int = 3000) -> None:
        if worker and worker.isRunning():
            worker.wait(timeout_ms)

    def closeEvent(self, event) -> None:
        self._clock_tmr.stop()
        if getattr(self, "_heartbeat_tmr", None):
            self._heartbeat_tmr.stop()
        if self.monitor:
            self.monitor.on_update = None
            self.monitor.stop()
        self.tts.on_speaking_start = None
        self.tts.on_speaking_end = None
        self.tts.on_log = None
        if self._live:
            self._live.stop()
        self.tts.stop()
        if self.dashboard:
            self.dashboard.stop()
        if self.relay:
            self.relay.stop()
        for worker in (self._worker, self._status_worker, self._sync_worker, getattr(self, "_pair_worker", None)):
            self._wait_worker(worker)
        super().closeEvent(event)


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Emo Desktop")
    win = EmoMainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
