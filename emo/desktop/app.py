"""Point d'entrée GUI PyQt6 — `py -3.11 -m emo.desktop` (sans --terminal)."""
from __future__ import annotations

import sys


def run_gui() -> None:
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        print("PyQt6 requis pour l'interface graphique: pip install PyQt6", file=sys.stderr)
        raise SystemExit(1)

    from emo.desktop.ui import EmoMainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Emo Desktop")
    win = EmoMainWindow()
    win.show()
    raise SystemExit(app.exec())
