"""
Point d'entrée Emo Desktop.

GUI (défaut):
    py -3.11 -m emo.desktop

Terminal (sans PyQt6):
    py -3.11 -m emo.desktop --terminal
    py -3.11 -m emo.desktop --terminal --once --text "bonjour"
    py -3.11 -m emo.desktop --terminal --no-mic
"""
from __future__ import annotations

# Fix Windows SSL — avant tout import HTTPS (Mark-XLVIII main.py)
try:
    import pip_system_certs.wrapt_requests  # noqa: F401
except ImportError:
    try:
        import certifi
        import os

        os.environ.setdefault("SSL_CERT_FILE", certifi.where())
        os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
    except ImportError:
        pass

from emo.desktop.cli.terminal import build_parser, run_terminal


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if getattr(args, "test_suite", False):
        from emo.desktop.cli.test_suite import run_random_suite

        raise SystemExit(run_random_suite(10))
    if args.terminal:
        raise SystemExit(run_terminal())
    from emo.desktop.app import run_gui

    run_gui()


if __name__ == "__main__":
    main()
