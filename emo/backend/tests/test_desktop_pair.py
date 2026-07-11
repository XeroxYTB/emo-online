"""Tests appairage dashboard desktop."""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from emo.desktop.dashboard.server import create_app, _get_pair_code, site_link_url


def test_pair_get_html():
    app = create_app()
    client = TestClient(app)
    r = client.get("/pair", headers={"Accept": "text/html"})
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert _get_pair_code() in r.text
    assert "Continuer sur Emo Online" in r.text


def test_site_link_url_format():
    url = site_link_url("AB12CD", 8000)
    assert "/link-desktop?code=AB12CD&port=8000" in url
    assert url.startswith("https://")


def test_pair_site_tokens_with_code():
    app = create_app()
    client = TestClient(app)
    code = _get_pair_code()
    with patch(
        "emo.desktop.dashboard.server._save_cloud_tokens",
        new_callable=AsyncMock,
        return_value={"conversation_id": "conv-1"},
    ):
        r = client.post(
            "/pair",
            json={
                "code": code,
                "session_token": "sess-test",
                "agent_token": "agent-test",
                "email": "u@test.com",
            },
        )
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert data.get("type") == "site_paired"
