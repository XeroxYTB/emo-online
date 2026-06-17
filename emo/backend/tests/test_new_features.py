"""Tests for Iteration 2 features: default mode 'tech', mode normal alias,
persona simplification (no 'hugo catala', no spontaneous lore), admin-only
project-export, and agent_relay truncation of large stdout."""
import os
import json
import uuid
import requests
import pytest

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://emo-personal.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "huglostalatac@gmail.com"
ADMIN_PASSWORD = "emo2026"

UNIQUE = uuid.uuid4().hex[:8]
NONADMIN_EMAIL = f"test_nonadmin_{UNIQUE}@example.com"
NONADMIN_PASSWORD = "emo-test-2026"
NONADMIN_NAME = f"NonAdmin {UNIQUE}"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def nonadmin_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/signup", json={
        "email": NONADMIN_EMAIL, "password": NONADMIN_PASSWORD, "name": NONADMIN_NAME
    })
    assert r.status_code == 200, f"signup failed: {r.status_code} {r.text}"
    return s


# ---------- Mode defaults & alias ----------

def test_create_conversation_default_mode_is_tech(admin_session):
    """POST /api/conversations without specifying mode → mode should be 'tech'."""
    r = admin_session.post(f"{API}/conversations", json={"title": "TEST_default_mode"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["mode"] == "tech", f"expected default mode 'tech', got '{data.get('mode')}'"
    # cleanup
    admin_session.delete(f"{API}/conversations/{data['conversation_id']}")


def _stream(session, conv_id, content, mode):
    r = session.post(
        f"{API}/chat/stream",
        json={"conversation_id": conv_id, "content": content, "mode": mode},
        stream=True,
        timeout=120,
    )
    assert r.status_code == 200, r.text
    deltas, done, err = [], None, None
    for line in r.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        p = json.loads(line[6:])
        if p["type"] == "delta":
            deltas.append(p["content"])
        elif p["type"] == "done":
            done = p
        elif p["type"] == "error":
            err = p
    return "".join(deltas), done, err


def test_chat_stream_mode_normal_legacy_treated_as_tech(admin_session):
    """Legacy mode='normal' should be silently mapped to tech (no error)."""
    rc = admin_session.post(f"{API}/conversations", json={"mode": "normal"})
    cid = rc.json()["conversation_id"]
    full, done, err = _stream(admin_session, cid, "Dis salut court.", "normal")
    assert err is None, f"stream error with legacy mode normal: {err}"
    assert done is not None
    assert len(full) > 0
    admin_session.delete(f"{API}/conversations/{cid}")


# ---------- Persona simplification ----------

def test_persona_no_full_name_no_spontaneous_lore(admin_session):
    """Asking 'qui es-tu ?' as admin must NOT contain 'hugo catala' or
    long-winded 'I'm Hugo's AI / DeskBuddy' lore."""
    rc = admin_session.post(f"{API}/conversations", json={"mode": "tech"})
    cid = rc.json()["conversation_id"]
    full, done, err = _stream(admin_session, cid, "Qui es-tu ?", "tech")
    assert err is None
    low = full.lower()
    # MUST NOT contain the full name
    assert "hugo catala" not in low, f"Persona leak — full name used: {full}"
    # Should still identify as Émo
    assert "émo" in low or "emo" in low, f"Emo identity missing: {full}"
    # Should NOT claim Claude
    for phrase in ["je suis claude", "i am claude", "modèle anthropic"]:
        assert phrase not in low, f"Claude identity leak: {full}"
    admin_session.delete(f"{API}/conversations/{cid}")


# ---------- Admin-only project export ----------

def test_project_export_nonadmin_forbidden(nonadmin_session):
    r = nonadmin_session.get(f"{API}/admin/project-export", allow_redirects=False)
    assert r.status_code == 403, f"non-admin should get 403, got {r.status_code}"


def test_project_export_admin_ok(admin_session):
    r = admin_session.get(f"{API}/admin/project-export", stream=True, timeout=60)
    assert r.status_code == 200, f"admin export failed: {r.status_code}"
    # Expect tar.gz or octet-stream
    ctype = r.headers.get("content-type", "")
    assert "gzip" in ctype or "octet-stream" in ctype or "tar" in ctype, f"unexpected content-type: {ctype}"
    # Read a bit to confirm body is gzip magic bytes
    chunk = next(r.iter_content(chunk_size=4), b"")
    r.close()
    assert chunk[:2] == b"\x1f\x8b", f"not a gzip stream, first bytes: {chunk!r}"


# ---------- Stripe webhook still works ----------

def test_stripe_webhook_upgrades_license(nonadmin_session):
    """Send a fake checkout.session.completed for the non-admin → license becomes paid."""
    me_before = nonadmin_session.get(f"{API}/auth/me").json()
    user_id = me_before["user_id"]
    lic_before = nonadmin_session.get(f"{API}/license/status").json()
    assert lic_before.get("source") == "free", f"non-admin already paid: {lic_before}"
    payload = {
        "id": f"evt_test_{uuid.uuid4().hex[:8]}",
        "type": "checkout.session.completed",
        "data": {"object": {"client_reference_id": user_id, "id": "cs_test_123"}},
    }
    r = requests.post(f"{API}/webhook/stripe", json=payload, timeout=30)
    assert r.status_code == 200, f"webhook failed: {r.status_code} {r.text}"
    lic_after = nonadmin_session.get(f"{API}/license/status").json()
    assert lic_after.get("source") == "stripe", f"license source not stripe after webhook: {lic_after}"
    assert lic_after.get("status") == "active", f"status not active after webhook: {lic_after}"


# ---------- Agent_relay truncation (unit-level via direct import) ----------

def test_agent_relay_truncates_large_stdout():
    """_truncate_large_fields should cap stdout to 64 KB (kept = last bytes)."""
    import sys
    sys.path.insert(0, "/app/backend")
    from agent_relay import _truncate_large_fields, _MAX_FIELD_BYTES

    huge = "A" * 200_000  # 200 KB
    payload = {"id": "req_1", "result": {"stdout": huge, "stderr": "", "exit_code": 0}}
    out = _truncate_large_fields(payload)
    stdout_after = out["result"]["stdout"]
    # Truncation marker prefix + last 64KB kept
    assert len(stdout_after) < 200_000
    assert out["result"].get("stdout_truncated") is True
    assert "backend-truncated" in stdout_after
    # Last byte of kept tail = 'A' (since huge is all 'A')
    assert stdout_after.endswith("A" * 16), "tail should be preserved"
    # Size of preserved tail is exactly _MAX_FIELD_BYTES
    # (prefix line + 64KB)
    assert stdout_after.count("A") == _MAX_FIELD_BYTES
