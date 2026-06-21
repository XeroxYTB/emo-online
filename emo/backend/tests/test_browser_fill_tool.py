"""browser_fill enregistré dans les outils navigateur."""
from browser_control import BROWSER_CONTROL_TOOL_NAMES, BROWSER_CONTROL_TOOLS


def test_browser_fill_registered():
    assert "browser_fill" in BROWSER_CONTROL_TOOL_NAMES
    names = [t["function"]["name"] for t in BROWSER_CONTROL_TOOLS]
    assert "browser_fill" in names
